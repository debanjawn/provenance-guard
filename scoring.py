LLM_WEIGHT = 0.45
STYLOMETRIC_WEIGHT = 0.30
PREDICTABILITY_WEIGHT = 0.25

LIKELY_HUMAN_MAX = 0.39
LIKELY_AI_MIN = 0.75
STRONG_AI_PATTERN_RULE = "strong_ai_pattern_agreement"
STRONG_AI_PATTERN_LLM_MIN = 0.80
STRONG_AI_PATTERN_PREDICTABILITY_MIN = 0.70


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

    llm_contribution = LLM_WEIGHT * llm_score
    stylometric_contribution = STYLOMETRIC_WEIGHT * stylometric_score
    predictability_contribution = PREDICTABILITY_WEIGHT * predictability_score

    combined_score = _clamp(
        llm_contribution
        + stylometric_contribution
        + predictability_contribution
    )
    calibration_rule_applied = False
    calibration_rule = None

    if (
        llm_score >= STRONG_AI_PATTERN_LLM_MIN
        and predictability_score >= STRONG_AI_PATTERN_PREDICTABILITY_MIN
        and combined_score < LIKELY_AI_MIN
    ):
        combined_score = LIKELY_AI_MIN
        calibration_rule_applied = True
        calibration_rule = STRONG_AI_PATTERN_RULE

    if combined_score >= LIKELY_AI_MIN:
        attribution = "likely_ai"
    elif combined_score > LIKELY_HUMAN_MAX:
        attribution = "uncertain"
    else:
        attribution = "likely_human"

    return {
        "confidence": round(combined_score, 4),
        "attribution": attribution,
        "classification_thresholds": {
            "likely_human_max": LIKELY_HUMAN_MAX,
            "likely_ai_min": LIKELY_AI_MIN,
        },
        "signal_scores": {
            "llm": llm_score,
            "stylometric": stylometric_score,
            "predictability": predictability_score,
        },
        "signal_contributions": {
            "llm": round(llm_contribution, 4),
            "stylometric": round(stylometric_contribution, 4),
            "predictability": round(predictability_contribution, 4),
        },
        "calibration_summary": {
            "weights": {
                "llm": LLM_WEIGHT,
                "stylometric": STYLOMETRIC_WEIGHT,
                "predictability": PREDICTABILITY_WEIGHT,
            },
            "calibration_rule_applied": calibration_rule_applied,
            "calibration_rule": calibration_rule,
            "distance_to_likely_ai": round(max(0.0, LIKELY_AI_MIN - combined_score), 4),
            "distance_to_likely_human": round(max(0.0, combined_score - LIKELY_HUMAN_MAX), 4),
            "explanation": (
                "Likely AI requires a high combined score or strong agreement between elevated LLM and "
                "predictability signals, so polished writing alone can still remain uncertain."
            ),
        },
    }
