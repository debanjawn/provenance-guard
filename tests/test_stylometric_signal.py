from detectors.stylometric_signal import get_stylometric_signal


LONG_TEXT = (
    "I drafted this paragraph during a slow train ride home, and I kept revising it as the "
    "stations passed by. Some sentences are short. Others wander a bit because I was thinking "
    "through a memory, changing direction, adding detail, and then cutting it back again."
)


def test_empty_text_does_not_crash():
    result = get_stylometric_signal("")

    assert result["score"] == 0.5
    assert "reason" in result
    assert result["metrics"] == {}


def test_short_text_returns_expected_shape():
    result = get_stylometric_signal("Too short to judge reliably.")

    assert "score" in result
    assert "reason" in result
    assert "metrics" in result
    assert 0.0 <= result["score"] <= 1.0
    assert "word_count" in result["metrics"]


def test_long_text_returns_metrics_and_bounded_score():
    result = get_stylometric_signal(LONG_TEXT)

    assert "score" in result
    assert "reason" in result
    assert "metrics" in result
    assert 0.0 <= result["score"] <= 1.0
    assert {
        "sentence_length_variance",
        "type_token_ratio",
        "punctuation_density",
        "repetition_rate",
    }.issubset(result["metrics"])
