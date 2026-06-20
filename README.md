# 🔍 KYC Job Finder

A Python application that runs daily, pulls KYC / AML / financial-crime compliance job postings from the [Adzuna](https://developer.adzuna.com/) API (free tier, 1,000 calls/month), rates each job against your CV using an LLM via [OpenRouter](https://openrouter.ai/), and pushes matches to your phone. Runs automatically on **GitHub Actions** for free.

## How it works

```
Adzuna API ──→ dedupe ──→ OpenRouter LLM ──→ filter by score ──→ push notification
                   │              │
               seen.db        your CV PDF
```

1. **Fetch** — Pulls recent KYC/AML job postings from Adzuna (free API).
2. **Dedupe** — Skips jobs already seen in previous runs (SQLite `seen.db`).
3. **Rate** — Each new job is scored 0–100 against your CV by an LLM on OpenRouter.
4. **Filter** — Only jobs scoring ≥ `MIN_SCORE` (default 70) are kept.
5. **Output** — Pushes a notification to your phone via **ntfy.sh**, or if SMTP is configured, emails you.

## Prerequisites

### 1. Adzuna API key (free)
- Go to [developer.adzuna.com/signup](https://developer.adzuna.com/signup) and register (free, no credit card)
- You'll receive an **App ID** and **App Key**
- Free tier = 1,000 calls/month — plenty for daily runs

### 2. OpenRouter key
- Sign up at [openrouter.ai](https://openrouter.ai)
- Go to [Keys](https://openrouter.ai/keys) and create an API key
- Add a few dollars of credit (DeepSeek models are very cheap — ~$0.02 per run)

### 3. ntfy.sh (free push notifications)
- Install the [ntfy](https://ntfy.sh/) app on your phone (iOS/Android)
- Pick a unique topic name and put it in your `.env` as `NTFY_TOPIC`

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
| `ADZUNA_APP_ID` | Your Adzuna App ID (free) |
| `ADZUNA_APP_KEY` | Your Adzuna App Key (free) |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `NTFY_TOPIC` | Your ntfy.sh topic name (e.g. `kyc-jobs-abc123`) |
| `LOCATION` | e.g. `United Kingdom` or `Remote` |
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
| `ADZUNA_APP_ID` | *required* | Adzuna App ID (free, sign up at developer.adzuna.com) |
| `ADZUNA_APP_KEY` | *required* | Adzuna App Key |
| `OPENROUTER_API_KEY` | *required* | OpenRouter API key |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v4-flash` | LLM model for rating |
| `NTFY_TOPIC` | *(optional)* | ntfy.sh topic for push notifications |
| `SMTP_HOST` | `smtp.protonmail.ch` | SMTP server (optional) |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(optional)* | SMTP login |
| `SMTP_PASS` | *(optional)* | SMTP app password |
| `EMAIL_TO` | *(optional)* | Recipient email |
| `SEARCH_QUERIES` | `KYC analyst, AML analyst, ...` | Comma-separated queries |
| `LOCATION` | `United Kingdom` | Job location |
| `MIN_SCORE` | `70` | Minimum score to include |
| `MAX_JOBS_PER_RUN` | `40` | Max jobs to rate per run |
| `CV_PATH` | `cv.pdf` | Path to CV PDF |

## Cost estimate

- **Adzuna**: Free tier — 1,000 calls/month. Each run uses 5 calls. More than enough.
- **OpenRouter**: DeepSeek V4 Flash costs ~$0.01 per run. A $5 top-up will last months.
- **ntfy.sh**: Completely free, no account needed.
- **GitHub Actions**: Free for public repos.

## License

MIT