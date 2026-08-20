"""
AI layer: turns the structured score + top factors into a plain-English
underwriting rationale.

Design: this is intentionally NOT the source of the credit decision -
the GradientBoosting model and fixed decision thresholds in ml/score.py
are. The LLM only narrates a decision that has already been made from
structured, auditable inputs. This is a deliberate guardrail: an LLM
should explain a regulated financial decision, not make it.

If ANTHROPIC_API_KEY is set, we call Claude to generate a natural
rationale grounded strictly in the provided factors (prompt forbids
inventing new reasons). Otherwise we fall back to a deterministic
template so the API works fully offline / without any key.
"""
import os

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except ImportError:
        return None


SYSTEM_PROMPT = (
    "You are an underwriting assistant that explains credit decisions to "
    "applicants in plain, respectful English. Rules you must follow: "
    "(1) Only reference the factors provided to you - never invent a "
    "reason not present in the input. "
    "(2) Never state or imply a protected characteristic (race, religion, "
    "gender, age-as-discrimination, national origin) as a reason. "
    "(3) Keep it to 3-5 sentences. "
    "(4) Be factual and neutral, not apologetic or effusive. "
    "(5) If the decision is DECLINE or REFER, mention one concrete, "
    "generic lever the applicant could improve (e.g. lowering "
    "debt-to-income ratio), without guaranteeing future approval."
)


def _template_explanation(decision: str, top_factors: list, behavioral: dict | None) -> str:
    risk_up = [f["feature"] for f in top_factors if f["direction"] == "increases_risk"][:3]
    risk_down = [f["feature"] for f in top_factors if f["direction"] == "decreases_risk"][:3]

    parts = []
    if decision == "APPROVE":
        parts.append("This application is recommended for approval.")
        if risk_down:
            parts.append(f"Key supporting factors: {', '.join(risk_down)}.")
    elif decision == "REFER":
        parts.append("This application is borderline and is routed to a human underwriter for review.")
        if risk_up:
            parts.append(f"Factors adding risk: {', '.join(risk_up)}.")
        if risk_down:
            parts.append(f"Offsetting strengths: {', '.join(risk_down)}.")
    else:
        parts.append("This application is recommended for decline based on the current risk profile.")
        if risk_up:
            parts.append(f"Primary risk drivers: {', '.join(risk_up)}.")
        parts.append("Reducing overall debt-to-income ratio or credit utilization is the most direct lever to improve future eligibility.")

    if behavioral:
        parts.append(
            f"Behavioral account signals were also reviewed (trust score {behavioral['behavioral_trust_score']}/100) "
            "as a supplementary, non-decisive input."
        )
    return " ".join(parts)


def generate_explanation(decision: str, top_factors: list, behavioral: dict | None = None) -> str:
    client = _get_client()
    if client is None:
        return _template_explanation(decision, top_factors, behavioral)

    factor_lines = "\n".join(
        f"- {f['feature']}: {f['direction'].replace('_', ' ')}" for f in top_factors
    )
    behavior_line = ""
    if behavioral:
        behavior_line = f"\nBehavioral trust score (supplementary, not decisive): {behavioral['behavioral_trust_score']}/100"

    user_prompt = (
        f"Decision: {decision}\n"
        f"Top factors (already computed, do not add others):\n{factor_lines}"
        f"{behavior_line}\n\n"
        "Write the applicant-facing explanation."
    )

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text").strip()
    except Exception:
        # Never let an LLM outage break the underwriting response -
        # fall back to the deterministic template.
        return _template_explanation(decision, top_factors, behavioral)
