AI_TOOLS = {
    "chatgpt",
    "midjourney",
    "dall-e",
    "dalle",
    "stable diffusion",
    "firefly",
    "runway",
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _is_truthy(value) -> bool:
    return value is True


def analyze_metadata(metadata: dict) -> dict:
    if not isinstance(metadata, dict) or not metadata:
        return {
            "content_type": "unknown",
            "provenance_score": 0.5,
            "metadata_attribution": "uncertain_process",
            "reason": "Metadata was missing or incomplete, so the provenance result is uncertain.",
            "metadata_checks": {},
        }

    score = 0.5
    tool_used = str(metadata.get("tool_used", "")).strip()
    normalized_tool = tool_used.casefold()

    declared_ai_assistance = _is_truthy(metadata.get("declared_ai_assistance"))
    has_process_notes = _is_truthy(metadata.get("has_process_notes"))
    edit_history_available = _is_truthy(metadata.get("edit_history_available"))
    human_reviewed = _is_truthy(metadata.get("human_reviewed"))
    tool_flagged = normalized_tool in AI_TOOLS

    if declared_ai_assistance:
        score += 0.3
    if tool_flagged:
        score += 0.25
    if has_process_notes:
        score -= 0.2
    if edit_history_available:
        score -= 0.2
    if human_reviewed:
        score -= 0.1

    score = _clamp(score)

    if score >= 0.80:
        metadata_attribution = "likely_ai_assisted"
        reason = "The metadata indicates stronger signs of AI-assisted creation than human-process evidence."
    elif score >= 0.40:
        metadata_attribution = "uncertain_process"
        reason = "The metadata shows mixed provenance signals, so the process result is uncertain."
    else:
        metadata_attribution = "likely_human_process"
        reason = "The metadata shows stronger signs of human process documentation than AI-assisted creation."

    return {
        "content_type": str(metadata.get("content_type", "unknown")),
        "provenance_score": round(score, 4),
        "metadata_attribution": metadata_attribution,
        "reason": reason,
        "metadata_checks": {
            "declared_ai_assistance": declared_ai_assistance,
            "tool_used": tool_used,
            "tool_flagged_as_ai": tool_flagged,
            "has_process_notes": has_process_notes,
            "edit_history_available": edit_history_available,
            "human_reviewed": human_reviewed,
        },
    }
