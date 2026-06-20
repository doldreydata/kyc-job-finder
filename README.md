# 🔍 KYC Job Finder

A Python application that runs daily, pulls KYC / AML / financial-crime compliance job postings from the [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) aggregator API, rates each job against your CV using an LLM via [OpenRouter](https://openrouter.ai/), and emails you the strong matches. Runs automatically on **GitHub Actions**.

## How it works

```
JSearch API ──→ dedupe ──→ OpenRouter LLM ──→ filter by score ──→ email
                  │              │
              seen.db        your CV PDF
```

1. **Fetch** — Pulls recent KYC/AML job postings from JSearch (covers LinkedIn, Indeed, Glassdoor, etc.).
2. **Dedupe** — Skips jobs already seen in previous runs (SQLite `seen.db`).
3. **Rate** — Each new job is scored 0–100 against your CV by an LLM on OpenRouter.
4. **Filter** — Only jobs scoring ≥ `MIN_SCORE` (default 70) are kept.
5. **Output** — If SMTP is configured, emails you the matches. Otherwise, prints them to the console (visible in GitHub Actions logs or your terminal).

## Prerequisites

### 1. RapidAPI key (JSearch)
- Sign up at [rapidapi.com](https://rapidapi.com)
- Subscribe to the [JSearch API](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) **free tier** (50 requests/month)
- Copy your RapidAPI key from the JSearch API page

### 2. OpenRouter key
- Sign up at [openrouter.ai](https://openrouter.ai)
- Go to [Keys](https://openrouter.ai/keys) and create an API key
- Add a few dollars of credit (DeepSeek models are very cheap — ~$0.02 per run)

### 3. SMTP email (optional)
Only needed if you want email alerts. No SMTP = results print to console (free).

**ProtonMail:** requires a paid plan for SMTP tokens
**Gmail:** requires a free App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
**Alternative:** leave SMTP blank and results will show in your terminal / GitHub Actions log.

## Local setup

```bash
# Clone the repo
cd kyc-job-finder

# Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in the env file
cp .env.example .env
# Edit .env with your real keys

# Place your CV as cv.pdf in the project root
cp /path/to/your/cv.pdf ./cv.pdf

# Run
python main.py
```

## GitHub Actions setup

### Secrets

Go to your repo → **Settings → Secrets and variables → Actions** and add these secrets:

| Secret | Description |
|---|---|
| `JSEARCH_API_KEY` | Your RapidAPI key |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_MODEL` | LLM model (default: `google/gemini-2.5-flash`) |
| `SMTP_HOST` | `smtp.protonmail.ch` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | Your ProtonMail/Gmail address (leave blank to skip email) |
| `SMTP_PASS` | Your ProtonMail/Gmail App Password (leave blank to skip email) |
| `EMAIL_TO` | Where to send alerts (not needed if SMTP is blank) |
| `SEARCH_QUERIES` | Comma-separated queries |
| `LOCATION` | e.g. `United Kingdom` or `Remote` |
| `MIN_SCORE` | Minimum score (default `70`) |
| `MAX_JOBS_PER_RUN` | Max LLM calls per run (default `40`) |
| `CV_PDF_BASE64` | Your CV encoded as base64 |

### Encoding your CV

```bash
base64 -w0 cv.pdf > cv_base64.txt
```

Copy the **entire** contents of `cv_base64.txt` into the `CV_PDF_BASE64` secret.

### Schedule

The workflow runs automatically **every day at 07:00 UTC**. You can also trigger it manually from the **Actions** tab → **Run workflow**.

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `JSEARCH_API_KEY` | *required* | RapidAPI key |
| `OPENROUTER_API_KEY` | *required* | OpenRouter API key |
| `OPENROUTER_MODEL` | `google/gemini-2.5-flash` | LLM model for rating |
| `SMTP_HOST` | `smtp.protonmail.ch` | SMTP server (ProtonMail or Gmail) |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *required* | SMTP login |
| `SMTP_PASS` | *required* | SMTP app password |
| `EMAIL_TO` | *required* | Recipient email |
| `SEARCH_QUERIES` | `KYC analyst, AML analyst, ...` | Comma-separated queries |
| `LOCATION` | `United Kingdom` | Job location |
| `MIN_SCORE` | `70` | Minimum score to email |
| `MAX_JOBS_PER_RUN` | `40` | Max jobs to rate per run |
| `CV_PATH` | `cv.pdf` | Path to CV PDF |

## Cost estimate

- **JSearch**: Free tier gives 50 requests/month. Each run uses N queries (default 5), so ~150 requests/month. You may need the $10/month Pro plan.
- **OpenRouter**: Gemini Flash models cost ~$0.15/million tokens. Rating 40 jobs at ~3K tokens each ≈ 120K tokens ≈ **$0.02 per run**.
- **GitHub Actions**: Free for public repos; 2,000 minutes/month for private repos.

## License

MIT