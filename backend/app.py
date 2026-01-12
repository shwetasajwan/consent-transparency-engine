from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json
import os

from dotenv import load_dotenv
from google import genai

# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------
app = FastAPI(title="Consent Transparency Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# LOAD RISK RULES
# --------------------------------------------------
with open("risk_rules.json", "r") as f:
    RISK_RULES = json.load(f)

# --------------------------------------------------
# DATA MODEL
# --------------------------------------------------
class ConsentInput(BaseModel):
    app_name: str
    permissions: list[str]
    policy_text: str

# --------------------------------------------------
# GEMINI LLM FUNCTION
# --------------------------------------------------
def simplify_policy(text: str) -> dict:
    """
    Uses Gemini to summarize consent text and extract risk flags.
    Falls back to deterministic rules if LLM fails.
    """
    try:
        prompt = f"""
You are a consent transparency AI.

Tasks:
1. Explain the privacy policy in ONE simple sentence.
2. Identify risks ONLY from this list:
   - THIRD_PARTY_SHARING
   - MARKETING
   - LONG_TERM_RETENTION

Rules:
- THIRD_PARTY_SHARING: data shared with partners, vendors, insurers, etc.
- MARKETING: promotions, offers, advertising, communication
- LONG_TERM_RETENTION: data kept "as long as necessary", 
  "for legal/business reasons", or "after termination"

Return ONLY valid JSON:
{{
  "summary": "...",
  "flags": ["FLAG1", "FLAG2"]
}}

Privacy Policy:
{text}
"""

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        output = response.text.strip()
        return json.loads(output)

    except Exception:
        # --------------------------------------------------
        # SAFE FALLBACK (NO LLM DEPENDENCY)
        # --------------------------------------------------
        summary = "This app collects and uses your data."
        flags = []

        lower = text.lower()

        if "third" in lower or "partner" in lower or "provider" in lower:
            flags.append("THIRD_PARTY_SHARING")
            summary += " It may share data with third parties."

        if "marketing" in lower or "promotional" in lower or "offers" in lower:
            flags.append("MARKETING")
            summary += " Data may be used for marketing."

        if (
            "retain" in lower
            or "as long as necessary" in lower
            or "after termination" in lower
            or "legal requirements" in lower
            or "business requirements" in lower
        ):
            flags.append("LONG_TERM_RETENTION")
            summary += " Your data may be retained long-term, even after service ends."

        return {
            "summary": summary,
            "flags": flags
        }

# --------------------------------------------------
# RISK SCORING
# --------------------------------------------------
def calculate_risk(permissions, flags):
    score = 0
    reasons = []

    for p in permissions:
        if p in RISK_RULES:
            score += RISK_RULES[p]
            reasons.append(p)

    for f in flags:
        if f in RISK_RULES:
            score += RISK_RULES[f]
            reasons.append(f)

    if score <= 3:
        level = "Low"
    elif score <= 6:
        level = "Medium"
    else:
        level = "High"

    return score, level, reasons

# --------------------------------------------------
# API ENDPOINT
# --------------------------------------------------
@app.post("/analyze-consent")
def analyze_consent(data: ConsentInput):
    ai_result = simplify_policy(data.policy_text)

    score, level, reasons = calculate_risk(
        data.permissions,
        ai_result["flags"]
    )

    return {
        "app": data.app_name,
        "plain_english_summary": ai_result["summary"],
        "risk_score": score,
        "risk_level": level,
        "why_it_matters": reasons
    }
