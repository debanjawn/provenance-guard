from scoring import LIKELY_AI_MIN, LIKELY_HUMAN_MAX, combine_scores


def test_low_combined_scores_produce_likely_human():
    result = combine_scores(
        {"score": 0.1},
        {"score": 0.2},
        {"score": 0.1},
    )

    assert result["attribution"] == "likely_human"
    assert result["confidence"] < 0.4


def test_middle_combined_scores_produce_uncertain():
    result = combine_scores(
        {"score": 0.5},
        {"score": 0.5},
        {"score": 0.5},
    )

    assert result["attribution"] == "uncertain"
    assert result["confidence"] == 0.5


def test_high_combined_scores_produce_likely_ai():
    result = combine_scores(
        {"score": 0.9},
        {"score": 0.9},
        {"score": 0.9},
    )

    assert result["attribution"] == "likely_ai"
    assert result["confidence"] == 0.9


def test_weighted_formula_uses_documented_weights():
    result = combine_scores(
        {"score": 1.0},
        {"score": 0.5},
        {"score": 0.2},
    )

    expected_confidence = round((0.45 * 1.0) + (0.30 * 0.5) + (0.25 * 0.2), 4)

    assert result["confidence"] == expected_confidence


def test_signal_scores_are_included_in_output():
    result = combine_scores(
        {"score": 0.25},
        {"score": 0.5},
        {"score": 0.75},
    )

    assert result["signal_scores"] == {
        "llm": 0.25,
        "stylometric": 0.5,
        "predictability": 0.75,
    }


def test_thresholds_and_contributions_are_included_in_output():
    result = combine_scores(
        {"score": 0.8},
        {"score": 0.75},
        {"score": 0.75},
    )

    assert result["classification_thresholds"] == {
        "likely_human_max": LIKELY_HUMAN_MAX,
        "likely_ai_min": LIKELY_AI_MIN,
    }
    assert result["signal_contributions"] == {
        "llm": 0.36,
        "stylometric": 0.225,
        "predictability": 0.1875,
    }
    assert result["calibration_summary"]["calibration_rule_applied"] is False
    assert result["calibration_summary"]["calibration_rule"] is None
    assert result["calibration_summary"]["distance_to_likely_ai"] == 0.0


def test_obvious_multi_signal_case_reaches_likely_ai_at_demo_threshold():
    result = combine_scores(
        {"score": 0.8},
        {"score": 0.75},
        {"score": 0.75},
    )

    assert result["confidence"] == 0.7725
    assert result["attribution"] == "likely_ai"


def test_strong_ai_pattern_agreement_rule_lifts_borderline_case():
    result = combine_scores(
        {"score": 0.8},
        {"score": 0.2},
        {"score": 0.7},
    )

    assert result["confidence"] == 0.75
    assert result["attribution"] == "likely_ai"
    assert result["calibration_summary"]["calibration_rule_applied"] is True
    assert result["calibration_summary"]["calibration_rule"] == "strong_ai_pattern_agreement"


def test_high_llm_alone_does_not_trigger_strong_ai_pattern_rule():
    result = combine_scores(
        {"score": 0.85},
        {"score": 0.2},
        {"score": 0.4},
    )

    assert result["attribution"] == "uncertain"
    assert result["confidence"] == 0.5425
    assert result["calibration_summary"]["calibration_rule_applied"] is False


def test_high_predictability_alone_does_not_trigger_strong_ai_pattern_rule():
    result = combine_scores(
        {"score": 0.6},
        {"score": 0.2},
        {"score": 0.8},
    )

    assert result["attribution"] == "uncertain"
    assert result["confidence"] == 0.53
    assert result["calibration_summary"]["calibration_rule_applied"] is False
