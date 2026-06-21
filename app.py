import streamlit as st
import fitz  # PyMuPDF
import re
import json
import os
import requests
import time
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="FactCheck — Verification Desk",
    page_icon="🖋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Design system: "wire desk" case-file aesthetic ──────────
# Paper-dark ledger background, typewriter display face, mono
# utility face for evidence/metadata, ink-stamp verdict badges.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Special+Elite&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #17160f;
    --bg-panel: #1d1c14;
    --ink: #ece6d6;
    --ink-dim: #9b9382;
    --rule: #3a3527;
    --accent: #c9a23e;
    --verified: #7a9b5e;
    --inaccurate: #c9952f;
    --false: #b5483d;
}

html, body, .stApp {
    background-color: var(--bg) !important;
    background-image: linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 100% 30px;
}
.block-container { padding-top: 2rem; }

/* Typography */
* { font-family: 'Inter', sans-serif; }
h1 {
    font-family: 'Special Elite', monospace !important;
    color: var(--ink) !important;
    letter-spacing: 1px;
    font-size: 2.4rem !important;
    margin-bottom: 0 !important;
}
h2, h3 { color: var(--ink) !important; font-family: 'Inter', sans-serif; font-weight: 600 !important; }
p, span, label, .stMarkdown { color: var(--ink) !important; }
.eyebrow {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--accent);
    letter-spacing: 3px;
    font-size: 0.78rem;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.subtitle { color: var(--ink-dim) !important; font-size: 1.02rem; margin-top: 4px; }
hr, [data-testid="stDivider"] { border-color: var(--rule) !important; opacity: 1 !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--bg-panel) !important;
    border-right: 1px solid var(--rule);
}
[data-testid="stSidebar"] * { color: var(--ink) !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: var(--bg-panel);
    border: 1px solid var(--rule);
    border-radius: 2px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 0.72rem !important;
    color: var(--ink-dim) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: var(--ink) !important;
}

/* Buttons */
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {
    background-color: var(--accent) !important;
    color: #1a1810 !important;
    border: 1px solid var(--accent) !important;
    border-radius: 2px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.15s ease;
}
div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {
    background-color: transparent !important;
    color: var(--accent) !important;
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--bg-panel) !important;
    border: 1px dashed var(--rule) !important;
    border-radius: 2px !important;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--ink-dim) !important; }

/* Tabs styled like folder tabs */
[data-testid="stTabs"] button {
    font-family: 'IBM Plex Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 0.8rem !important;
    color: var(--ink-dim) !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Selectbox / inputs */
[data-baseweb="select"] { background-color: var(--bg-panel) !important; }
[data-testid="stSelectbox"] * { color: var(--ink) !important; }

/* Progress bar */
[data-testid="stProgress"] > div > div { background-color: var(--accent) !important; }

/* Expander */
[data-testid="stExpander"] {
    background-color: var(--bg-panel) !important;
    border: 1px solid var(--rule) !important;
    border-radius: 2px !important;
}

/* ── Evidence entry: the claim card, redesigned as a case-file row ── */
.entry {
    position: relative;
    background: var(--bg-panel);
    border: 1px solid var(--rule);
    border-left: 3px solid var(--rule);
    border-radius: 2px;
    padding: 18px 20px 16px 20px;
    margin: 14px 0;
}
.entry.verified { border-left-color: var(--verified); }
.entry.inaccurate { border-left-color: var(--inaccurate); }
.entry.false { border-left-color: var(--false); }

.entry-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--ink-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
}
.entry-claim {
    font-size: 1.02rem;
    color: var(--ink);
    margin: 8px 0 12px 0;
    line-height: 1.45;
}
.entry-body {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.86rem;
    color: var(--ink-dim);
    line-height: 1.6;
}
.entry-body b { color: var(--ink); font-weight: 600; }

/* Ink-stamp verdict badge — the signature element */
.stamp {
    display: inline-block;
    font-family: 'Special Elite', monospace;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 0.95rem;
    padding: 4px 14px;
    border: 2px solid currentColor;
    border-radius: 3px;
    transform: rotate(-3deg);
    float: right;
    margin-left: 12px;
}
.stamp.verified { color: var(--verified); }
.stamp.inaccurate { color: var(--inaccurate); }
.stamp.false { color: var(--false); }

/* Hide Streamlit's default chrome: toolbar (Fork/Deploy), hamburger menu, footer */
[data-testid="stToolbar"] { visibility: hidden; height: 0; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ── Models (in fallback order) ─────────────────────────────
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


def get_api_key() -> str:
    """
    Pulls the Gemini API key from Streamlit secrets or an env var.
    NEVER hardcode the key in source — it gets pushed to git history
    and anyone can scrape/use it.
    """
    key = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, "secrets") else None
    if not key:
        key = os.environ.get("GEMINI_API_KEY")
    return key


def gemini_call(prompt: str, use_search: bool = False, retries: int = 3) -> tuple[str, str]:
    """Returns (response_text, model_used)."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to .streamlit/secrets.toml "
            "or as an environment variable."
        )

    last_error = ""
    for model in MODELS:
        for attempt in range(retries):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2048,
                }
            }
            if use_search:
                body["tools"] = [{"google_search": {}}]

            try:
                resp = requests.post(url, json=body, timeout=60)
            except requests.exceptions.Timeout:
                last_error = f"{model} timed out"
                time.sleep(3)
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"{model} request error: {e}"
                break

            if resp.status_code == 200:
                data = resp.json()
                try:
                    parts = data["candidates"][0]["content"]["parts"]
                    text_parts = [p["text"] for p in parts if "text" in p]
                    return "\n".join(text_parts), model
                except (KeyError, IndexError):
                    last_error = f"Unexpected response from {model}"
                    break

            elif resp.status_code == 429:
                wait = 8 * (attempt + 1)
                time.sleep(wait)
                last_error = f"429 on {model}"
                continue

            elif resp.status_code == 400 and use_search:
                body.pop("tools", None)
                resp2 = requests.post(url, json=body, timeout=60)
                if resp2.status_code == 200:
                    data = resp2.json()
                    try:
                        parts = data["candidates"][0]["content"]["parts"]
                        text_parts = [p["text"] for p in parts if "text" in p]
                        return "\n".join(text_parts), model
                    except (KeyError, IndexError):
                        pass
                last_error = f"{model} 400: {resp.text[:200]}"
                break

            else:
                last_error = f"{model} {resp.status_code}: {resp.text[:200]}"
                break

    raise ValueError(f"All models failed. Last error: {last_error}")


def fix_truncated_json(s: str) -> str:
    stack = []
    in_string = False
    escape = False
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '[{':
            stack.append(ch)
        elif ch in ']}':
            if stack:
                stack.pop()

    if in_string:
        s += '"'
    s = s.rstrip().rstrip(',')
    closing = {'{': '}', '[': ']'}
    for opener in reversed(stack):
        s += closing[opener]
    return s


def safe_parse_json(raw: str):
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"^```\s*", "", raw.strip())
    raw = re.sub(r"```\s*$", "", raw.strip()).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            try:
                return json.loads(fix_truncated_json(match.group(0)))
            except Exception:
                pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            try:
                return json.loads(fix_truncated_json(match.group(0)))
            except Exception:
                pass

    try:
        return json.loads(fix_truncated_json(raw))
    except Exception:
        pass

    raise ValueError(f"Cannot parse JSON. Raw response:\n{raw[:400]}")


@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


@st.cache_data(show_spinner=False)
def extract_claims_cached(text_hash: str, text: str, max_claims: int):
    """Cached wrapper keyed on a hash of the text so repeated runs on the
    same document don't re-spend an API call."""
    prompt = f"""Extract up to {max_claims} specific, verifiable factual claims from this text.
Focus on: statistics, percentages, dates, financial figures, named entities with attributed facts.

Rules:
- Keep each claim under 120 characters
- Return ONLY a valid complete JSON array, nothing else
- Do NOT truncate the array — include the closing ]
- No markdown, no explanation

Format exactly like this:
[
  {{"claim": "Apple was founded in 1976 by Steve Jobs", "category": "date"}},
  {{"claim": "Global smartphone market is worth $500 billion", "category": "financial"}}
]

Category: stat / date / financial / technical / other

Text to analyze:
{text[:4000]}"""
    raw, _ = gemini_call(prompt, use_search=False)
    result = safe_parse_json(raw)
    if isinstance(result, dict):
        result = [result]
    return result


def verify_claim(claim: str) -> dict:
    prompt = f"""Fact-check this claim using web search.

CLAIM: "{claim}"

You MUST classify the claim as one of exactly 3 verdicts:
- VERIFIED: the claim is accurate and matches current data
- INACCURATE: the claim is outdated or partially wrong (provide the correct fact)
- FALSE: use this for any of the following — the claim is contradicted by evidence,
  OR it is not a checkable factual claim (e.g. an opinion, belief, or nonsense statement),
  OR there is insufficient evidence to confirm it either way

Reply with ONLY this JSON (no markdown, no extra text):
{{"verdict": "VERIFIED", "confidence": 90, "explanation": "short reason here", "correct_fact": null, "source": "source name"}}

Rules:
- verdict must be exactly: VERIFIED, INACCURATE, or FALSE — nothing else
- correct_fact: provide the real/current fact if verdict is INACCURATE or FALSE, else null
- explanation: if verdict is FALSE because the claim could not be verified or is not a
  factual claim, say so explicitly (e.g. "Not a verifiable factual claim" or
  "Insufficient evidence to confirm"), rather than implying it was disproven
- Keep all string values under 200 characters"""
    try:
        raw, model_used = gemini_call(prompt, use_search=True)
        result = safe_parse_json(raw)
        verdict = result.get("verdict", "FALSE").upper().strip()
        if verdict not in ("VERIFIED", "INACCURATE", "FALSE"):
            verdict = "FALSE"
        return {
            "verdict": verdict,
            "confidence": result.get("confidence", 0),
            "explanation": result.get("explanation", "No explanation provided."),
            "correct_fact": result.get("correct_fact"),
            "source": result.get("source", "N/A"),
            "model_used": model_used,
        }
    except Exception as e:
        return {
            "verdict": "FALSE",
            "confidence": 0,
            "explanation": f"Verification error: {str(e)[:150]}",
            "correct_fact": None,
            "source": "N/A",
            "model_used": "N/A",
        }


def verdict_meta(verdict):
    meta = {
        "VERIFIED": ("HOLDS", "verified"),
        "INACCURATE": ("PARTIAL", "inaccurate"),
        "FALSE": ("VOID", "false"),
    }
    return meta.get(verdict, ("VOID", "false"))


def render_entry(r: dict, index: int):
    stamp_word, css_class = verdict_meta(r.get("verdict", "FALSE"))
    confidence = r.get("confidence", 0)
    model_used = r.get("model_used", "")
    correct = f"<br><b>Correct fact —</b> {r['correct_fact']}" if r.get("correct_fact") else ""

    st.markdown(f"""
    <div class="entry {css_class}">
        <span class="stamp {css_class}">{stamp_word}</span>
        <div class="entry-tag">EXHIBIT {index:02d} · {r.get('category', '').upper()} · {confidence}% CONFIDENCE</div>
        <div class="entry-claim">{r['claim']}</div>
        <div class="entry-body">
            <b>Finding —</b> {r.get('explanation', '')}{correct}<br>
            <b>Source —</b> {r.get('source', 'N/A')} &nbsp;&nbsp; <b>Model —</b> {model_used or 'N/A'}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar settings ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### CONTROL PANEL")
    max_claims = st.slider("Max claims to extract", 3, 15, 8)
    max_workers = st.slider(
        "Parallel verification workers", 1, 5, 3,
        help="Higher = faster, but more likely to hit rate limits (429s)."
    )
    st.divider()
    st.markdown("**Key status**")
    if get_api_key():
        st.success("API key loaded")
    else:
        st.error("No API key found — add GEMINI_API_KEY to secrets.toml")
    st.divider()
    st.caption("Built by Kishan · Powered by Gemini Flash + Google Search")

# ── Header ───────────────────────────────────────────────────
st.markdown('<div class="eyebrow">AUTOMATED VERIFICATION DESK</div>', unsafe_allow_html=True)
st.markdown("# FactCheck")
st.markdown(
    '<div class="subtitle">Upload a document. Every claim gets pulled, checked against live search, and stamped with a verdict.</div>',
    unsafe_allow_html=True
)
st.write("")

col1, col2, col3, col4 = st.columns(4)
col1.metric("ENGINE", "Gemini Flash")
col2.metric("SOURCE", "Live Search")
col3.metric("VERDICTS", "3 Types")
col4.metric("COST", "Free")

st.divider()

uploaded_file = st.file_uploader("Submit a PDF for review", type=["pdf"], help="Max 10MB")

if uploaded_file:
    file_bytes = uploaded_file.read()
    text_hash = hashlib.md5(file_bytes).hexdigest()

    with st.spinner("Reading document..."):
        text = extract_text_from_pdf(file_bytes)

    st.success(f"Extracted {len(text):,} characters from the document")
    with st.expander("Preview extracted text"):
        st.text(text[:1500] + ("..." if len(text) > 1500 else ""))

    if not get_api_key():
        st.error("Cannot run fact-check: no API key configured. See sidebar.")
        st.stop()

    if st.button("Open Case", type="primary", use_container_width=True):
        with st.spinner("Pulling claims from the document..."):
            try:
                claims = extract_claims_cached(text_hash, text, max_claims)
            except Exception as e:
                st.error(f"Claim extraction failed: {e}")
                st.stop()

        if not claims:
            st.warning("No verifiable claims found in this document.")
            st.stop()

        if len(claims) > max_claims:
            st.info(f"Found {len(claims)} claims — reviewing the top {max_claims} to stay within free rate limits.")
            claims = claims[:max_claims]
        else:
            st.markdown(f"**{len(claims)} claims entered for review**")

        # ── Parallel verification ───────────────────────────
        results = []
        progress = st.progress(0)
        status_text = st.empty()
        done = 0
        total = len(claims)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_claim = {
                executor.submit(verify_claim, c.get("claim", str(c))): c
                for c in claims
            }
            for future in as_completed(future_to_claim):
                claim_obj = future_to_claim[future]
                claim_text = claim_obj.get("claim", str(claim_obj))
                result = future.result()
                result["claim"] = claim_text
                result["category"] = claim_obj.get("category", "other")
                results.append(result)
                done += 1
                progress.progress(done / total)
                status_text.text(f"Reviewed {done}/{total}")

        status_text.empty()
        progress.empty()

        # Keep results in the original claim order
        order = {c.get("claim", str(c)): i for i, c in enumerate(claims)}
        results.sort(key=lambda r: order.get(r["claim"], 0))

        st.session_state["results"] = results
        st.session_state["case_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Results display (persisted across reruns) ────────────────
if "results" in st.session_state:
    results = st.session_state["results"]
    verdicts = [r.get("verdict", "FALSE") for r in results]
    v_count = sum(1 for v in verdicts if v == "VERIFIED")
    i_count = sum(1 for v in verdicts if v == "INACCURATE")
    f_count = sum(1 for v in verdicts if v == "FALSE")

    st.divider()
    st.markdown(
        f'<div class="entry-tag">CASE LOG · {st.session_state.get("case_date", "")}</div>',
        unsafe_allow_html=True
    )
    tab_summary, tab_details, tab_export = st.tabs(["SUMMARY", "EXHIBITS", "EXPORT"])

    with tab_summary:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("HOLDS", v_count)
        mc2.metric("PARTIAL", i_count)
        mc3.metric("VOID", f_count)

    with tab_details:
        filter_choice = st.selectbox(
            "Filter by verdict",
            ["All", "VERIFIED", "INACCURATE", "FALSE"]
        )
        filtered = results if filter_choice == "All" else [
            r for r in results if r.get("verdict") == filter_choice
        ]
        for idx, r in enumerate(filtered, start=1):
            render_entry(r, idx)

    with tab_export:
        st.download_button(
            "Download full report — JSON",
            data=json.dumps(results, indent=2),
            file_name="factcheck_report.json",
            mime="application/json"
        )

        csv_lines = ["claim,verdict,confidence,category,explanation,correct_fact,source"]
        for r in results:
            row = [
                str(r.get("claim", "")).replace(",", ";"),
                r.get("verdict", ""),
                str(r.get("confidence", "")),
                r.get("category", ""),
                str(r.get("explanation", "")).replace(",", ";"),
                str(r.get("correct_fact", "") or "").replace(",", ";"),
                str(r.get("source", "")).replace(",", ";"),
            ]
            csv_lines.append(",".join(row))
        st.download_button(
            "Download report — CSV",
            data="\n".join(csv_lines),
            file_name="factcheck_report.csv",
            mime="text/csv"
        )

st.divider()
st.markdown('<div class="entry-tag">Built by Kishan · Powered by Gemini Flash + Google Search</div>', unsafe_allow_html=True)
