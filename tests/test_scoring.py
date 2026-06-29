from scoring import combine_scores


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
