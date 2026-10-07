import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal
from app.routers import auth, business, readiness, transactions

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("kudiready")

if settings.environment == "production" and (len(settings.jwt_secret) < 32 or settings.jwt_secret.startswith("dev-only")):
    raise RuntimeError("JWT_SECRET must be set to a random 32+ character value in production")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Turns Nigerian MSME bank and mobile-money statements into an explainable credit-readiness profile.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # bearer tokens, no cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Simple sliding-window limiter for credential endpoints. Per-process, which
# is adequate for a single instance; a multi-instance deploy would move this
# to Redis (see report §7, "Scalability").
_AUTH_WINDOW_S, _AUTH_MAX = 60, 10
_auth_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()

    if request.url.path in ("/v1/auth/login", "/v1/auth/register") and request.method == "POST":
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0]
        hits = _auth_hits[ip]
        now = time.monotonic()
        while hits and now - hits[0] > _AUTH_WINDOW_S:
            hits.popleft()
        if len(hits) >= _AUTH_MAX:
            return JSONResponse({"detail": "Too many attempts, try again in a minute"}, status_code=429)
        hits.append(now)

    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    log.info("rid=%s %s %s -> %s %.0fms", rid, request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


app.include_router(auth.router)
app.include_router(business.router)
app.include_router(transactions.router)
app.include_router(readiness.router)


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    db_ok = True
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "version": app.version}


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs", "health": "/healthz"}
