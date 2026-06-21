# FactCheck — Automated Verification Desk

A web app that fact-checks PDF documents using **Gemini AI + live Google Search**. Upload a PDF, and every verifiable claim gets pulled out, checked against live search, and stamped with a verdict.

## What It Does

1. **Extract** — Upload a PDF; the AI identifies verifiable claims (statistics, dates, financial figures, technical facts)
2. **Verify** — Each claim is checked in parallel against live web data via Google Search (Gemini grounding)
3. **Report** — Claims are stamped with one of three verdicts:
   - ✅ **VERIFIED (HOLDS)** — matches current data
   - ⚠️ **INACCURATE (PARTIAL)** — outdated or partially wrong (correct fact provided)
   - ❌ **FALSE (VOID)** — contradicted by evidence, OR not a checkable factual claim, OR insufficient evidence to confirm either way

## Live Demo

**Deployed App:** <https://fact-check-app.streamlit.app/>

## Setup & Run Locally

### Prerequisites

- Python 3.9+
- A [Google AI Studio](https://aistudio.google.com/) API key (free)

### Installation

```bash
git clone https://github.com/Kishan269565/factcheck-app.git
cd factcheck-app
pip install -r requirements.txt
```

### Configure your API key

The app reads the key from Streamlit secrets — it is **never** hardcoded in source.

Create `.streamlit/secrets.toml` in the project root:

```toml
GEMINI_API_KEY = "your-api-key-here"
```

Add this file to `.gitignore` so it never gets committed (already included in this repo's `.gitignore`).

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Deploy to Streamlit Cloud

1. Push this repository to GitHub
2. Go to <https://share.streamlit.io>
3. Connect your GitHub repo and set `app.py` as the main file
4. Go to **Settings → Secrets** and add:
   ```toml
   GEMINI_API_KEY = "your-api-key-here"
   ```
5. Click **Deploy**

## Tech Stack

| Component   | Technology                                       |
| ----------- | ------------------------------------------------- |
| Frontend    | Streamlit                                          |
| AI Model    | Gemini 2.5 Flash / 2.0 Flash / 1.5 Flash (auto-fallback chain) |
| Web Search  | Google Search grounding (Gemini native tool)       |
| PDF Parsing | PyMuPDF (`fitz`)                                   |
| Concurrency | `ThreadPoolExecutor` — claims verified in parallel |
| Deployment  | Streamlit Cloud                                    |

## How It Works

```
PDF Upload → Text Extraction → Claim Extraction (Gemini)
                                       ↓
                  Parallel Claim Verification (Gemini + Google Search)
                                       ↓
                  Verdict: VERIFIED / INACCURATE / FALSE
                                       ↓
                  Downloadable Report (JSON or CSV)
```

## Features

- **Parallel verification** — claims are checked concurrently (configurable worker count) instead of sequentially, cutting wait time significantly
- **Caching** — PDF text extraction and claim extraction are cached, so re-running on the same document doesn't burn extra API calls
- **Sidebar controls** — adjust max claims extracted and parallel worker count without touching code
- **Filterable results** — view all claims or filter by verdict
- **Export** — download the full report as JSON or CSV
- **Custom UI** — case-file/evidence-desk visual theme; Streamlit's default toolbar and menu are hidden

## Evaluation

Tested against documents containing intentional false claims and outdated statistics. The system:

- Flags fabricated statistics and outdated figures
- Provides corrected facts with source attribution
- Distinguishes "contradicted by evidence" from "not a checkable claim" in its explanations, even though both currently fall under the same FALSE verdict

## Project Structure

```
factcheck-app/
├── app.py                       # Main Streamlit application
├── requirements.txt             # Python dependencies
├── .streamlit/secrets.toml      # Local API key (gitignored, not in repo)
└── README.md                    # This file
```

## Requirements

```
streamlit>=1.35.0
PyMuPDF>=1.23.0
requests>=2.31.0
```

## Known Limitations

- Free Gemini API tier has rate limits; the app includes automatic retry/backoff logic and a fallback chain across multiple models
- Claims are capped per run (configurable in the sidebar, default 8) to stay within free quota
- Very long PDFs are truncated for claim extraction (first ~4,000 characters)
- Claims that aren't genuine factual statements (opinions, beliefs, nonsense input) are grouped under the FALSE verdict rather than a separate category — the explanation text clarifies which case applies

## Security Notes

- API keys are loaded via `st.secrets` / environment variables only — never hardcoded
- If you ever see a "API key was reported as leaked" or "API key expired" error, generate a new key in Google AI Studio and update it in both your local `secrets.toml` and Streamlit Cloud's Secrets settings
- Never commit `.streamlit/secrets.toml` — check `git status` before `git add .` if you're unsure

---

## Snapshot

*(screenshots pending update for the new UI)*

## Built By

Kishan · Powered by Gemini Flash + Google Search
