import os


# ============================================================
# CREDME — LLM NARRATIVE EXPLANATION LAYER
# ============================================================
#
# Turns a structured /decision result into a short, plain-
# English narrative for the applicant. This is layered ON TOP
# of the deterministic SHAP + rule-based reasoning that already
# drives the actual decision (see backend/api.py) — the LLM
# never sees raw applicant PII beyond what's already in the
# decision payload, and never influences the decision itself.
# It only rephrases an already-made, already-explainable
# decision into more readable prose.
#
# CREDME_LLM_API_KEY is intentionally unset in this environment.
# Without it, generate_narrative_explanation() returns a
# clearly-labeled template-based narrative (source:
# "template_fallback") instead of calling out to a real model —
# the integration is real and wired, but no live LLM call is
# made unless a key is explicitly configured. See README.md.
#
# ============================================================

LLM_API_KEY = os.environ.get("CREDME_LLM_API_KEY")

LLM_MODEL = os.environ.get("CREDME_LLM_MODEL", "claude-sonnet-5")


# ------------------------------------------------------------
# Prompt template
# ------------------------------------------------------------
#
# Deliberately constrained: the model is given ONLY the fields
# already surfaced by the deterministic decision engine, and is
# explicitly instructed not to introduce new claims, not to
# reference protected characteristics, and not to imply the
# decision could change on request.
#
# ------------------------------------------------------------

PROMPT_TEMPLATE = """You are writing a short, plain-English explanation of a \
credit decision for the applicant who received it. You are NOT making the \
decision — it has already been made by a separate, deterministic system. \
Your only job is to explain the decision that was already made, using \
ONLY the facts given below. Do not invent additional reasons.

Decision: {final_decision}
Credit strength: {credit_strength}
Thin-file (no traditional credit history): {thin_file}
Behavioral risk level: {behavioral_risk}
Top credit factors: {top_reasons}
Financial concerns noted: {financial_concerns}
Existing system-generated reasoning: {reasoning}

Rules:
- 3-5 sentences, plain English, neutral and respectful tone.
- Do not mention age, gender, race, religion, marital status, disability, \
national origin, or any other protected characteristic, even if it \
appears in the input.
- Do not claim the decision could change if the applicant asks again.
- Do not describe internal model mechanics (SHAP values, feature weights, \
thresholds) — describe the REASONS in plain terms instead.
- If thin-file is true, make clear the missing credit score was not \
treated as a negative signal.
"""


# ------------------------------------------------------------
# Guardrails
# ------------------------------------------------------------
#
# A minimal, illustrative output guardrail: scans generated
# text for protected-characteristic language that should never
# appear in a lending explanation, regardless of source. A
# production system would pair this with a second LLM-based
# judge pass; this keyword screen is intentionally simple and
# auditable rather than another opaque model call.
#
# ------------------------------------------------------------

GUARDRAIL_BANNED_TERMS = [
    "race", "racial", "ethnicity", "gender", "sex", "religion",
    "religious", "disability", "disabled", "national origin",
    "immigration status", "sexual orientation",
]

SAFE_FALLBACK_NARRATIVE = (
    "This decision was based on the applicant's credit profile, "
    "financial indicators, and recent account activity. A detailed, "
    "itemized breakdown is available in the reasons provided with this "
    "decision."
)


def apply_guardrails(text):
    lowered = text.lower()

    violations = [
        term for term in GUARDRAIL_BANNED_TERMS if term in lowered
    ]

    if violations:
        return SAFE_FALLBACK_NARRATIVE, violations

    return text, []


def build_prompt(decision):
    top_reasons = ", ".join(
        f"{r['feature']} ({r['effect']})"
        for r in decision.get("reasons", [])[:5]
    ) or "none listed"

    financial_concerns = (
        ", ".join(decision.get("financial_concerns", []))
        or "none"
    )

    return PROMPT_TEMPLATE.format(
        final_decision=decision.get("final_decision"),
        credit_strength=decision.get("credit_strength"),
        thin_file=decision.get("thin_file"),
        behavioral_risk=decision.get("behavioral_risk"),
        top_reasons=top_reasons,
        financial_concerns=financial_concerns,
        reasoning=decision.get("reasoning"),
    )


def _template_fallback_narrative(decision):
    """
    Deterministic, non-LLM narrative used whenever no LLM API
    key is configured. Reuses the same fields the prompt would,
    so behavior is consistent whether or not a key is set.
    """

    sentences = [decision.get("reasoning", "").strip()]

    if decision.get("thin_file"):
        sentences.append(
            "Because this applicant has no traditional credit history, "
            "that absence was not treated as a negative signal."
        )

    financial_concerns = decision.get("financial_concerns", [])
    if financial_concerns:
        sentences.append(
            "Additional factors reviewed: "
            + "; ".join(financial_concerns) + "."
        )

    behavioral_risk = decision.get("behavioral_risk")
    if behavioral_risk and behavioral_risk != "LOW":
        sentences.append(
            f"Recent account activity was assessed as {behavioral_risk} "
            "risk and factored into this outcome."
        )

    return " ".join(s for s in sentences if s)


def _call_llm(prompt):
    """
    Only reached when CREDME_LLM_API_KEY is set. Imports the
    SDK lazily so the rest of the app works without it
    installed when no key is configured.
    """

    import anthropic

    client = anthropic.Anthropic(api_key=LLM_API_KEY)

    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(
        block.text for block in response.content if block.type == "text"
    )


def generate_narrative_explanation(decision):
    prompt = build_prompt(decision)

    if LLM_API_KEY:
        raw_text = _call_llm(prompt)
        source = f"llm:{LLM_MODEL}"
    else:
        raw_text = _template_fallback_narrative(decision)
        source = "template_fallback"

    safe_text, violations = apply_guardrails(raw_text)

    return {
        "narrative": safe_text,
        "source": source,
        "guardrail_violations": violations,
        "prompt_used": prompt,
    }
