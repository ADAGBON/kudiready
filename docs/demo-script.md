# KudiReady — 10-minute presentation & demo script

**Setup before recording**
- Open the API `/healthz` URL 2 minutes early (wakes the free Render instance).
- Browser tabs: (1) the live app, logged out; (2) GitHub repo → Actions tab with a green run; (3) `docs/architecture.md` diagrams; (4) Render dashboard; (5) a private window for the lender link.
- Have `sample-statement.csv` and `sample-statement-feb-2026.csv` in Downloads.
- Use a fresh email (e.g. `demo+1@…`) so the account starts empty.
- Screen at 1280–1440 px wide, browser zoom 110%.

---

## 0:00 – 1:15 · The problem

**Show:** a title slide (or just the login page — its left panel is a good backdrop).

> "Nigeria has around 40 million micro, small and medium businesses. They make up close to half of GDP and most of the jobs. In PwC's 2024 MSME survey, access to finance was the single biggest growth challenge, and the IFC puts the unmet credit need at about 32 billion dollars.
>
> I spent five years at the Central Bank of Nigeria, in treasury and monetary statistics. What I saw is that many of these businesses aren't bad credit risks — they're *illegible* ones. The money moves through POS terminals, OPay and bank transfers, so the evidence exists. But nobody has turned it into the file a loan officer needs, and the owner doesn't know what's missing until they've been turned down.
>
> KudiReady does that one job: it turns a statement into a lender-ready credit file, and tells the owner exactly what to fix first. It doesn't lend and it doesn't make credit decisions."

## 1:15 – 2:30 · Architecture

**Show:** diagram 1 (system), then diagram 3 (data model).

> "It's a three-tier cloud app. A React and TypeScript single-page app on Vercel's edge CDN. A FastAPI service in Docker on Render, and a managed Postgres 16 database. They talk over HTTPS with JSON and a bearer token, and CORS only allows my frontend.
>
> Four tables. A few decisions worth calling out: money is stored as integer kobo, never floats. Every transaction has a fingerprint with a unique constraint, so re-uploading an overlapping statement can't double-count. For CAC and TIN we store yes or no only — never the numbers — that's data minimisation under the Nigeria Data Protection Act. And share links store only a hash of the token."

## 2:30 – 6:45 · Live demo

**2:30 — Sign up and profile (30 s)**
Create account → fill business: *Mama Ada Provisions*, Retail, Lagos, 4 years, 2 staff, tick only "business account".
> "Owners are mostly on phones, so it's all one column on mobile — I'll show that at the end."

**3:00 — Upload (45 s)**
Transactions → choose `sample-statement.csv`.
> "This is a synthetic statement in the debit/credit layout most Nigerian banks export. About 1,700 lines read, categorised and stored in well under a second."
Point at the categories column: POS → Sales, LAPO → Loan repayment, IKEDC → Power. Then re-upload the same file:
> "Uploading again — zero added, all skipped as duplicates."

**3:45 — Dashboard (1 min 15 s)**
Overview.
> "68 out of 100, Nearly ready. The score is four pillars of 25 — each tick is one point. Record quality, cash-flow strength, stability, and obligations.
> The chart shows February is missing — that gap is flagged in yellow. Margin is only 11%, which is why cash-flow strength is the weakest pillar.
> Every point is explained down here — no black box. A lender can see exactly why."
Point at the repayment-capacity figure and the footnote.

**5:00 — Fix list and improving the score (1 min)**
What to fix → read the top two items.
Transactions → upload `sample-statement-feb-2026.csv`. Filter "Not yet categorised", set a couple to *Other expense*.
Profile → tick CAC and TIN → Save.
Overview:
> "76. Same business, now a complete file. That's the loop: see the gap, fix it, see the score move."

**6:00 — Share with a lender (45 s)**
Share → label "LAPO Microfinance, Ikeja" → Create link → copy → open in private window.
> "No login needed. It's a frozen snapshot, it expires in 14 days, and the owner can revoke it."
Back in the app: refresh links (view count = 1), Revoke, reload the private window → "Link unavailable".

## 6:45 – 8:30 · Engineering quality

**Show:** GitHub Actions run, then `backend/tests`, then Render dashboard.

> "Every push runs three CI jobs. The API job lints, applies the Alembic migrations to a real Postgres 16 and checks they match the models, then runs 39 tests with a coverage gate at 85% — we're at 94%. The web job typechecks and builds. The Docker job builds the production image, boots it, and hits /healthz.
>
> Render deploys only after CI passes, and the whole backend is defined as code in render.yaml.
>
> Tests aren't just happy paths: one logs in as a second user and tries to read and delete the first user's transactions — 404 every time, because the business is always resolved from the token, never from the URL.
>
> Security in short: bcrypt passwords, signed JWTs, timing-safe login, rate limiting on auth endpoints, security headers, non-root container, and the API refuses to start in production with a weak secret."

## 8:30 – 9:30 · Results and limits

> "What works today: the full owner journey, the lender view, and a deployed, tested pipeline.
>
> One finding from testing changed the design: two months of strong-looking numbers scored 67. No lender would accept that, so I added an evidence cap — under three months you can't score above 35, under six not above 55.
>
> Limits I'd be honest about: the figures are self-uploaded, not verified with the bank. Categorisation is rules, not ML. And the scoring weights are informed by lender practice, not yet calibrated on loan outcomes."

## 9:30 – 10:00 · Next steps and close

> "Next: pull statements directly through CBN's open banking APIs so the data is verified at source; PDF statement parsing; and a pilot with an MFI to calibrate the weights against real repayment data.
>
> KudiReady: your statements already tell lenders your story — this makes sure they can read it. Thank you."

---

**If something breaks live:** switch to the screenshots in `docs/screenshots/` (they follow this exact order) and keep talking.
