import streamlit as st
import fitz  # PyMuPDF
import re
import json
import os
import requests
import time

st.set_page_config(
    page_title="FactCheck AI - Truth Layer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main { background: #0a1628; }
    .stApp { background: #0a1628; }
    h1, h2, h3 { color: #00c2ff !important; }
    .claim-card { padding: 16px; border-radius: 10px; margin: 10px 0; }
    .verified { background: #0a3d2e; border-left: 4px solid #00c874; }
    .inaccurate { background: #3d2a0a; border-left: 4px solid #ffd93d; }
    .false { background: #3d0a0a; border-left: 4px solid #ff6b6b; }
</style>
""", unsafe_allow_html=True)

# ✅ Correct working model names
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# 🔑 Hardcoded API Key
GEMINI_API_KEY = "AIzaSyB8YLXUlozNizjGPawQmJTnPCKZufhQ5xQ"

def get_api_key():
    return GEMINI_API_KEY


def gemini_call(prompt: str, use_search: bool = False, retries: int = 3) -> str:
    api_key = get_api_key()
    if not api_key:
        st.error("❌ GEMINI_API_KEY not set.")
        st.stop()

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
                time.sleep(5)
                continue

            if resp.status_code == 200:
                data = resp.json()
                try:
                    parts = data["candidates"][0]["content"]["parts"]
                    text_parts = [p["text"] for p in parts if "text" in p]
                    return "\n".join(text_parts)
                except (KeyError, IndexError):
                    last_error = f"Unexpected response from {model}"
                    break

            elif resp.status_code == 429:
                wait = 15 * (attempt + 1)
                st.toast(f"⏳ Rate limit on {model}. Waiting {wait}s...")
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
                        return "\n".join(text_parts)
                    except (KeyError, IndexError):
                        pass
                last_error = f"{model} 400: {resp.text[:200]}"
                break

            else:
                last_error = f"{model} {resp.status_code}: {resp.text[:200]}"
                break

        else:
            continue
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


def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def extract_claims(text: str):
    prompt = f"""Extract up to 8 specific, verifiable factual claims from this text.
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
{text[:2500]}"""

    raw = gemini_call(prompt, use_search=False)
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
- FALSE: the claim is clearly wrong with no supporting evidence

Reply with ONLY this JSON (no markdown, no extra text):
{{"verdict": "VERIFIED", "confidence": 90, "explanation": "short reason here", "correct_fact": null, "source": "source name"}}

Rules:
- verdict must be exactly: VERIFIED, INACCURATE, or FALSE — nothing else
- correct_fact: provide the real/current fact if verdict is INACCURATE or FALSE, else null
- Keep all string values under 200 characters"""

    try:
        raw = gemini_call(prompt, use_search=True)
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
        }
    except Exception as e:
        return {
            "verdict": "FALSE",
            "confidence": 0,
            "explanation": f"Verification error: {str(e)[:150]}",
            "correct_fact": None,
            "source": "N/A"
        }


def verdict_badge(verdict):
    badges = {
        "VERIFIED":   ("✅ VERIFIED",   "verified"),
        "INACCURATE": ("⚠️ INACCURATE", "inaccurate"),
        "FALSE":      ("❌ FALSE",       "false"),
    }
    return badges.get(verdict, ("❌ FALSE", "false"))


# ── UI ────────────────────────────────────────────────────
st.markdown("# 🔍 FactCheck AI")
st.markdown("### *Your Truth Layer for Marketing Content*")
st.markdown("Upload a PDF — Gemini AI extracts claims and cross-references them against **live Google Search** in real time.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Powered By", "Gemini Flash")
col2.metric("Web Search", "Google Search ✅")
col3.metric("Verdicts", "3 Types")
col4.metric("Cost", "100% Free 🎉")

delay = 6  # Default delay between claims

st.divider()

uploaded_file = st.file_uploader("📎 Upload PDF Document", type=["pdf"], help="Max 10MB")

if uploaded_file:
    with st.spinner("📄 Extracting text from PDF..."):
        text = extract_text_from_pdf(uploaded_file)

    st.success(f"✅ Extracted {len(text):,} characters from PDF")

    with st.expander("📝 Preview extracted text"):
        st.text(text[:1500] + ("..." if len(text) > 1500 else ""))

    if st.button("🚀 Run Fact-Check", type="primary", use_container_width=True):

        with st.spinner("🤖 Extracting verifiable claims..."):
            try:
                claims = extract_claims(text)
            except Exception as e:
                st.error(f"Claim extraction failed: {e}")
                st.stop()

        if not claims:
            st.warning("No verifiable claims found in this document.")
            st.stop()

        if len(claims) > 10:
            st.info(f"ℹ️ Found {len(claims)} claims — checking top 10 to stay within free rate limits.")
            claims = claims[:10]
        else:
            st.markdown(f"### 📋 Found **{len(claims)}** verifiable claims")

        results = []
        progress = st.progress(0)
        status_text = st.empty()

        for i, claim_obj in enumerate(claims):
            claim = claim_obj.get("claim", str(claim_obj))
            status_text.text(f"🔍 Verifying {i+1}/{len(claims)}: {claim[:80]}...")
            result = verify_claim(claim)
            result["claim"] = claim
            result["category"] = claim_obj.get("category", "other")
            results.append(result)
            progress.progress((i + 1) / len(claims))
            if i < len(claims) - 1:
                time.sleep(delay)

        status_text.empty()
        progress.empty()

        verdicts = [r.get("verdict", "FALSE") for r in results]
        v_count = sum(1 for v in verdicts if v == "VERIFIED")
        i_count = sum(1 for v in verdicts if v == "INACCURATE")
        f_count = sum(1 for v in verdicts if v == "FALSE")

        st.divider()
        st.markdown("## 📊 Results Summary")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("✅ Verified", v_count)
        mc2.metric("⚠️ Inaccurate", i_count)
        mc3.metric("❌ False", f_count)

        st.divider()
        st.markdown("## 🧾 Detailed Results")

        for r in results:
            label, css_class = verdict_badge(r.get("verdict", "FALSE"))
            correct = f"\n\n**✏️ Correct Fact:** {r['correct_fact']}" if r.get("correct_fact") else ""
            source = f"\n\n**🔗 Source:** {r.get('source', 'N/A')}"
            confidence = r.get("confidence", 0)

            st.markdown(f"""
<div class="claim-card {css_class}">
<strong>{label}</strong> &nbsp;&nbsp; <em>Confidence: {confidence}%</em> &nbsp;&nbsp; <code>{r.get('category','').upper()}</code><br><br>
<strong>Claim:</strong> {r['claim']}<br><br>
<strong>📌 Verdict:</strong> {r.get('explanation', '')}
{correct}{source}
</div>
""", unsafe_allow_html=True)

        st.download_button(
            "⬇️ Download Full Report (JSON)",
            data=json.dumps(results, indent=2),
            file_name="factcheck_report.json",
            mime="application/json"
        )

st.divider()
st.markdown("*Built for CogCulture GEO Assessment • Powered by Gemini Flash + Google Search*")
