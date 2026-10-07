#!/usr/bin/env bash
# One-shot: create the GitHub repo, push, and deploy the frontend to Vercel.
# Run from the unzipped kudiready folder on your own computer.
#
# Needs: git, GitHub CLI (gh) and Vercel CLI (npx vercel), each logged in once:
#   gh auth login        npx vercel login
#
# Usage:
#   ./scripts/ship.sh                       # step 1: GitHub repo + push
#   ./scripts/ship.sh https://<api>.onrender.com   # step 3: deploy frontend against your Render API
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${KUDI_REPO:-kudiready}"

if [ $# -eq 0 ]; then
  echo "==> Creating public GitHub repo '$REPO' and pushing…"
  if ! gh repo view "$REPO" >/dev/null 2>&1; then
    gh repo create "$REPO" --public --source=. --remote=origin --push \
      --description "Credit-readiness for Nigerian MSMEs — FastAPI, React, Postgres"
  else
    git remote get-url origin >/dev/null 2>&1 || git remote add origin "$(gh repo view "$REPO" --json url -q .url).git"
    git push -u origin main
  fi
  URL="$(gh repo view "$REPO" --json url -q .url)"
  echo
  echo "Pushed: $URL"
  echo "CI:     $URL/actions"
  echo
  echo "Next: deploy the API + database on Render (one click):"
  echo "  https://render.com/deploy?repo=$URL"
  echo "When it's live, copy its URL and run:  ./scripts/ship.sh https://<your-api>.onrender.com"
  exit 0
fi

API_URL="${1%/}"
echo "==> Checking API at $API_URL/healthz (free instances can take ~50s to wake)…"
for i in $(seq 1 12); do
  if curl -fsS "$API_URL/healthz" | grep -q '"database":true'; then echo "API healthy"; break; fi
  [ "$i" -eq 12 ] && { echo "API not healthy yet — check the Render logs, then re-run."; exit 1; }
  sleep 10
done

echo "==> Deploying frontend to Vercel…"
cd frontend
npx --yes vercel@latest link --yes --project "$REPO" >/dev/null
printf '%s' "$API_URL" | npx --yes vercel@latest env add VITE_API_URL production --force >/dev/null 2>&1 || true
WEB_URL="$(npx --yes vercel@latest deploy --prod --yes --build-env VITE_API_URL="$API_URL" | tail -1)"
cd ..

echo
echo "Frontend live: $WEB_URL"
echo
echo "Last step: in Render → kudiready-api → Environment, set"
echo "  CORS_ORIGINS = $WEB_URL"
echo "and save (it redeploys in ~1 min). Then open $WEB_URL and sign up."
