"""Article 50 transparency-notice generator for ActTrace.

Template-based, deterministic, pure Python — no LLM, no network, no DB.
Produces a transparency notice that discloses AI use and advises human
review of important output, tailored by ``notice_type`` and ``tone``.

Consumed by ``ActTraceService.generate_notice`` (see ``acttrace_service``).
"""
from __future__ import annotations

from acttrace.services.acttrace_constants import DISCLAIMER

# --- Supported value sets (mirror the BLUEPRINT contract) ------------------
NOTICE_TYPES = (
    "chatbot",
    "ai_generated_content",
    "support_assist",
    "summarization",
    "synthetic_media",
    "internal_ai",
    "other",
)

TONES = ("plain", "formal", "developer_docs", "policy", "ui_microcopy")

_DEFAULT_NOTICE_TYPE = "other"
_DEFAULT_TONE = "plain"
_DEFAULT_LANGUAGE = "en"
_HUMAN_REVIEW_NOT_RECOMMENDED = "required_before_action"

# Caveat that always points back to the spirit of DISCLAIMER. Kept short so it
# reads cleanly in a list; the full DISCLAIMER text is referenced verbatim too.
_NOT_LEGAL_ADVICE_CAVEAT = (
    "This notice is drafting support to help you communicate AI use under "
    "Article 50 of the EU AI Act. It is not legal advice and does not certify "
    "compliance. " + DISCLAIMER
)


# --- Per-notice-type wording -----------------------------------------------
# Each entry: a human label, the "what the AI does" verb phrase, and a
# "what the output is" noun phrase. Templates below weave these together.
_TYPE_PROFILE = {
    "chatbot": {
        "label": "AI chatbot",
        "action": "uses artificial intelligence to generate conversational "
                  "responses",
        "output_noun": "responses",
        "placement": "Display this notice at the start of the chat session "
                     "and keep it visible near the message input.",
    },
    "ai_generated_content": {
        "label": "AI-generated content",
        "action": "uses artificial intelligence to generate written content "
                  "on your behalf",
        "output_noun": "generated content",
        "placement": "Show this notice next to the generated content, with a "
                     "persistent 'AI-generated' label on each output.",
    },
    "support_assist": {
        "label": "AI-assisted support",
        "action": "uses artificial intelligence to draft and suggest support "
                  "answers",
        "output_noun": "suggested answers",
        "placement": "Show this notice in the support console where agents "
                     "see AI suggestions, before any reply is sent.",
    },
    "summarization": {
        "label": "AI summarization",
        "action": "uses artificial intelligence to summarize longer content",
        "output_noun": "summaries",
        "placement": "Display this notice directly above or beside each "
                     "AI-generated summary.",
    },
    "synthetic_media": {
        "label": "AI-generated synthetic media",
        "action": "uses artificial intelligence to create or alter images, "
                  "audio, or video",
        "output_noun": "synthetic media",
        "placement": "Apply a clear, visible label on the synthetic media "
                     "itself and repeat this notice wherever it is shared.",
    },
    "internal_ai": {
        "label": "internal AI assistance",
        "action": "uses artificial intelligence to assist internal staff",
        "output_noun": "AI-assisted output",
        "placement": "Show this notice in the internal tool's interface and "
                     "in onboarding documentation for staff users.",
    },
    "other": {
        "label": "AI feature",
        "action": "uses artificial intelligence to assist with this feature",
        "output_noun": "AI-assisted output",
        "placement": "Display this notice at the point of interaction, close "
                     "to where the AI output appears.",
    },
}


def _profile(notice_type: str) -> dict:
    return _TYPE_PROFILE.get(notice_type, _TYPE_PROFILE[_DEFAULT_NOTICE_TYPE])


def _subject(ai_system_name: str, feature_name: str, profile: dict) -> str:
    """Human-readable subject phrase, preferring caller-supplied names."""
    name = (feature_name or "").strip() or (ai_system_name or "").strip()
    if name:
        return name
    return "This " + profile["label"]


def _categories_clause(output_categories) -> str:
    """Optional clause listing the kinds of output the AI produces."""
    if not output_categories:
        return ""
    items = [str(c).strip() for c in output_categories if str(c).strip()]
    if not items:
        return ""
    if len(items) == 1:
        listed = items[0]
    elif len(items) == 2:
        listed = items[0] + " and " + items[1]
    else:
        listed = ", ".join(items[:-1]) + ", and " + items[-1]
    return "This includes " + listed + "."


# --- Tone renderers ---------------------------------------------------------
# Every renderer must (a) disclose AI use and (b) advise reviewing important
# output before relying on it. Tones differ visibly in wording and length.

def _body_plain(subject, action, output_noun, system_name, cats) -> str:
    parts = [
        f"{subject} {action}.",
        f"AI-generated {output_noun} may be incomplete or inaccurate.",
        "You should review important information before relying on it.",
    ]
    if cats:
        parts.insert(1, cats)
    return " ".join(parts)


def _body_formal(subject, action, output_noun, system_name, cats) -> str:
    sys_clause = f" (powered by {system_name})" if system_name else ""
    parts = [
        f"Please be advised that {subject.lower() if subject.startswith('This') else subject}"
        f"{sys_clause} {action}.",
        f"The {output_noun} produced by this artificial intelligence system "
        "may contain errors, omissions, or inaccuracies and should not be "
        "treated as authoritative.",
        "We strongly recommend that you carefully review any important "
        "information before relying upon it or acting on it.",
    ]
    if cats:
        parts.insert(1, cats)
    return " ".join(parts)


def _body_developer_docs(subject, action, output_noun, system_name, cats) -> str:
    sys_clause = f" The underlying system is {system_name}." if system_name else ""
    lines = [
        f"AI disclosure: {subject} {action}.{sys_clause}",
        "",
        f"Behaviour: the {output_noun} returned by this feature are "
        "generated by an AI model and are not deterministic guarantees of "
        "correctness. Treat them as probabilistic suggestions.",
    ]
    if cats:
        lines.append(cats)
    lines += [
        "",
        "Integration guidance: surface a visible AI-disclosure string to end "
        "users, and either keep a human in the loop or prompt users to "
        "verify important output before it is relied on or acted upon.",
    ]
    return "\n".join(lines)


def _body_policy(subject, action, output_noun, system_name, cats) -> str:
    sys_clause = f", implemented via {system_name}," if system_name else ""
    parts = [
        f"{subject}{sys_clause} {action}, and in accordance with the "
        "transparency requirements of Article 50 of the EU AI Act, users are "
        "hereby informed that they are interacting with, or receiving output "
        "from, an artificial intelligence system.",
        f"The {output_noun} generated by this system may be incomplete, "
        "inaccurate, or otherwise unsuitable for a given purpose.",
        "Users and operators remain responsible for reviewing important "
        "information and exercising appropriate human oversight before "
        "relying on such output.",
    ]
    if cats:
        parts.insert(1, cats)
    return " ".join(parts)


def _body_ui_microcopy(subject, action, output_noun, system_name, cats) -> str:
    # Deliberately the shortest tone — fits a tooltip or inline label.
    return (
        f"AI-powered: this {output_noun.rstrip('s') or 'output'} is "
        "generated by AI and may be inaccurate. Please double-check "
        "important details."
    )


_TONE_RENDERERS = {
    "plain": _body_plain,
    "formal": _body_formal,
    "developer_docs": _body_developer_docs,
    "policy": _body_policy,
    "ui_microcopy": _body_ui_microcopy,
}


def _placement_for(profile: dict, tone: str) -> str:
    base = profile["placement"]
    if tone == "developer_docs":
        return (base + " In documentation, place it in the feature's README "
                "or API reference under an 'AI transparency' heading.")
    if tone == "policy":
        return (base + " Also reference it from your terms of service or AI "
                "usage policy.")
    if tone == "ui_microcopy":
        return ("Use this as inline UI microcopy — e.g. a tooltip, helper "
                "text, or a small label adjacent to the AI output.")
    return base


def generate_notice(params: dict) -> dict:
    """Generate an EU AI Act Article 50 transparency notice.

    ``params`` keys: ``ai_system_name``, ``feature_name``, ``notice_type``,
    ``tone``, ``language``, ``output_categories`` (list),
    ``human_review_level``, ``risk_category`` (optional).

    Returns a dict with ``body``, ``suggested_placement``, ``caveats``,
    ``human_review_recommended``, and echoes ``notice_type``, ``tone``,
    ``language``.
    """
    params = params or {}

    ai_system_name = (params.get("ai_system_name") or "").strip()
    feature_name = (params.get("feature_name") or "").strip()

    notice_type = params.get("notice_type") or _DEFAULT_NOTICE_TYPE
    if notice_type not in NOTICE_TYPES:
        notice_type = _DEFAULT_NOTICE_TYPE

    tone = params.get("tone") or _DEFAULT_TONE
    if tone not in TONES:
        tone = _DEFAULT_TONE

    # English only for the MVP — echo whatever was asked but default to "en".
    language = params.get("language") or _DEFAULT_LANGUAGE

    output_categories = params.get("output_categories") or []
    human_review_level = params.get("human_review_level")

    profile = _profile(notice_type)
    subject = _subject(ai_system_name, feature_name, profile)
    cats = _categories_clause(output_categories)

    render = _TONE_RENDERERS[tone]
    body = render(
        subject,
        profile["action"],
        profile["output_noun"],
        ai_system_name,
        cats,
    )

    caveats = [
        _NOT_LEGAL_ADVICE_CAVEAT,
        "Adapt the wording to your product, audience, and jurisdiction "
        "before publishing it.",
        "Disclosure alone does not satisfy every AI Act obligation — confirm "
        "which obligations apply to your risk category.",
    ]
    if params.get("risk_category") in ("possible_high_risk", "prohibited"):
        caveats.append(
            "This use case may carry obligations beyond transparency; obtain "
            "qualified legal review before deployment."
        )

    human_review_recommended = (
        human_review_level != _HUMAN_REVIEW_NOT_RECOMMENDED
    )

    return {
        "body": body,
        "suggested_placement": _placement_for(profile, tone),
        "caveats": caveats,
        "human_review_recommended": human_review_recommended,
        "notice_type": notice_type,
        "tone": tone,
        "language": language,
    }
