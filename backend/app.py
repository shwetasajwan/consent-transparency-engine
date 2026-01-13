from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Consent Transparency Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("risk_rules.json", "r") as f:
    RISK_RULES = json.load(f)

class ConsentInput(BaseModel):
    app_name: str
    permissions: list[str]
    policy_text: str

def simplify_policy(text: str) -> dict:
    try:
        prompt = f"""
You are a consent transparency AI.

TASKS:
1. Explain the document in SIMPLE, EASY language.
2. Base the explanation ONLY on what is explicitly written in the document.
3. Mention specific details found in the text (organization type, activities, data handling, outsourcing, disclaimers, etc.).
4. Do NOT give a generic explanation.
5. Do NOT assume or mention any law, act, or regulation unless it is explicitly named in the document.
6. Two different documents must produce clearly different summaries.
7. Write 4–6 sentences.

Identify risks ONLY from this list:
- THIRD_PARTY_SHARING
- MARKETING
- LONG_TERM_RETENTION
- IMPLICIT_CONSENT
- OUTSOURCING_RISK
- LIMITED_LIABILITY
- COMPLEX_LEGAL_TEXT

Return ONLY valid JSON:
{{
  "summary": "content-grounded explanation here",
  "flags": ["FLAG1", "FLAG2"]
}}

DOCUMENT:
{text}
"""

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        parsed = json.loads(response.text.strip())

        return {
            "summary": parsed["summary"],
            "flags": parsed.get("flags", []),
            "source": "LLM"
        }

    except Exception:

        lower = text.lower()
        flags = []
        summary_parts = []

        if "public sector" in lower or "government" in lower:
            summary_parts.append(
                "This document is issued by a public sector or government-related organization and explains its internal governance and operations."
            )

        if "employee" in lower or "officer" in lower:
            summary_parts.append(
                "It describes the roles, responsibilities, and authority of employees and officials within the organization."
            )

        if "information" in lower or "records" in lower:
            summary_parts.append(
                "The document outlines what types of information are collected, maintained, and managed by the organization."
            )

        if "retain" in lower or "stored" in lower or "as long as necessary" in lower:
            summary_parts.append(
                "Certain information may be stored and retained for legal, audit, or compliance-related purposes."
            )
            flags.append("LONG_TERM_RETENTION")

        if "outsourc" in lower or "vendor" in lower or "third party" in lower:
            summary_parts.append(
                "Some activities or services mentioned may be handled by external or third-party service providers."
            )
            flags.extend(["OUTSOURCING_RISK", "THIRD_PARTY_SHARING"])

        if "reserves the right" in lower or "errors and omissions" in lower:
            summary_parts.append(
                "The organization reserves the right to correct errors or omissions, which limits responsibility in certain situations."
            )
            flags.append("LIMITED_LIABILITY")

        if "marketing" in lower or "advertis" in lower:
            flags.append("MARKETING")

        if "consent" not in lower:
            flags.append("IMPLICIT_CONSENT")

        if len(text) > 1200:
            flags.append("COMPLEX_LEGAL_TEXT")

        if not summary_parts:
            summary_parts.append(
                "This document explains rules, responsibilities, and procedures described in the provided text."
            )

        return {
            "summary": " ".join(summary_parts),
            "flags": list(set(flags)),
            "source": "FALLBACK"
        }

def calculate_risk(permissions, flags):
    score = 0
    reasons = []

    GOVERNANCE_RISKS = {
        "IMPLICIT_CONSENT",
        "OUTSOURCING_RISK",
        "LIMITED_LIABILITY",
        "COMPLEX_LEGAL_TEXT",
        "LONG_TERM_RETENTION",
        "THIRD_PARTY_SHARING"
    }

    governance_score = 0

    for p in permissions:
        if p in RISK_RULES:
            score += RISK_RULES[p]
            reasons.append(p)

    for f in flags:
        if f in RISK_RULES:
            if f in GOVERNANCE_RISKS:
                governance_score += RISK_RULES[f]
            else:
                score += RISK_RULES[f]
            reasons.append(f)

    governance_score = min(governance_score, 5)
    score += governance_score

    if not permissions:
        level = "Medium" if score > 3 else "Low"
    else:
        if score <= 3:
            level = "Low"
        elif score <= 7:
            level = "Medium"
        else:
            level = "High"

    return score, level, list(set(reasons))

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
        "why_it_matters": reasons,
        "analysis_source": ai_result["source"]
    }
