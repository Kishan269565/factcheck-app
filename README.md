# FactCheck AI — Truth Layer for Marketing Content

A deployed web app that automatically fact-checks PDF documents using **Gemini AI + live Google Search**.

## What It Does

1. **Extract** — Upload a PDF; the AI identifies all verifiable claims (statistics, dates, financial figures, technical facts)
2. **Verify** — Each claim is cross-referenced against live web data via Google Search (Gemini grounding)
3. **Report** — Claims are flagged as:
   - ✅ **VERIFIED** — matches current data
   - ⚠️ **INACCURATE** — outdated or partially wrong (correct fact provided)
   - ❌ **FALSE** — contradicted by evidence / no supporting data found

## Live Demo

**Deployed App:** [https://your-app.streamlit.app](https://your-app.streamlit.app) *(replace with your live URL)*

## Setup & Run Locally

### Prerequisites

- Python 3.9+
- A [Google AI Studio](https://aistudio.google.com/) API key (free)

### Installation

```bash
git clone https://github.com/your-username/factcheck-ai.git
cd factcheck-ai
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

> **Note:** The API key is currently hardcoded in `app.py` for demo purposes. For production, use environment variables or Streamlit Secrets.

## Deploy to Streamlit Cloud

1. Push this repository to GitHub
2. Go to [https://share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo and set `app.py` as the main file
4. (Optional) Add `GEMINI_API_KEY` under **Settings → Secrets** and update `get_api_key()` to use `st.secrets`
5. Click **Deploy**

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| AI Model | Gemini 2.5 Flash / 2.0 Flash (auto-fallback) |
| Web Search | Google Search grounding (Gemini native tool) |
| PDF Parsing | PyMuPDF (`fitz`) |
| Deployment | Streamlit Cloud |

## How It Works

```
PDF Upload → Text Extraction → Claim Identification (Gemini)
                                        ↓
                            Claim Verification (Gemini + Google Search)
                                        ↓
                            Verdict: VERIFIED / INACCURATE / FALSE
                                        ↓
                            Downloadable JSON Report
```

## Evaluation

Tested against "trap documents" containing intentional lies and outdated statistics. The system correctly:
- Flags fake statistics and hallucinated figures
- Provides corrected real facts with source attribution
- Handles PDFs up to 10MB with up to 10 claims per run

## Project Structure

```
factcheck-ai/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Requirements

```
streamlit>=1.35.0
PyMuPDF>=1.23.0
requests>=2.31.0
```

## Known Limitations

- Free Gemini API tier has rate limits; the app includes automatic retry and delay logic
- Claims are limited to 10 per run to stay within free quota
- Very long PDFs (>10,000 characters) are truncated for claim extraction

---

*Built for CogCulture GEO Assessment · Powered by Gemini Flash + Google Search*
