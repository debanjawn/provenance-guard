LIKELY_HUMAN_LABEL = (
    "This text appears more consistent with human-written work based on the signals "
    "reviewed. This label is not a guarantee, but the system did not find strong signs "
    "of AI generation."
)

UNCERTAIN_LABEL = (
    "We are not confident enough to determine whether this text was written by a person "
    "or generated with AI. This result should not be treated as a final judgment."
)

LIKELY_AI_LABEL = (
    "This text shows strong signs of AI generation based on multiple signals, but this "
    "is not a final judgment. The creator may appeal this label."
)


def generate_label(attribution: str, confidence: float) -> str:
    if attribution == "likely_human":
        return LIKELY_HUMAN_LABEL
    if attribution == "likely_ai":
        return LIKELY_AI_LABEL
    return UNCERTAIN_LABEL
