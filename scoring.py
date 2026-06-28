def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _get_score(signal: dict) -> float:
    return _clamp(signal.get("score", 0.5))


def combine_scores(
    llm_signal: dict,
    stylometric_signal: dict,
    predictability_signal: dict,
) -> dict:
    llm_score = _get_score(llm_signal)
    stylometric_score = _get_score(stylometric_signal)
    predictability_score = _get_score(predictability_signal)

    combined_score = _clamp(
        (0.45 * llm_score)
        + (0.30 * stylometric_score)
        + (0.25 * predictability_score)
    )

    if combined_score >= 0.80:
        attribution = "likely_ai"
    elif combined_score >= 0.40:
        attribution = "uncertain"
    else:
        attribution = "likely_human"

    return {
        "confidence": round(combined_score, 4),
        "attribution": attribution,
        "signal_scores": {
            "llm": llm_score,
            "stylometric": stylometric_score,
            "predictability": predictability_score,
        },
    }
