from detectors.predictability_signal import get_predictability_signal


FORMULAIC_TEXT = (
    "In today's world, it is important to note that technology plays a crucial role in daily life. "
    "In conclusion, it is important to note that technology plays a crucial role in education and work. "
    "Furthermore, there are many factors to consider, and overall, it is clear that technology plays a crucial role."
)

CASUAL_TEXT = (
    "I wrote this after dinner when the kitchen was finally quiet and the dog stopped barking at the window. "
    "I kept thinking about how my grandmother used to fold napkins into triangles, and that tiny habit still "
    "shows up whenever I host friends at home."
)


def test_empty_text_does_not_crash():
    result = get_predictability_signal("")

    assert result["score"] == 0.5
    assert "reason" in result
    assert result["metrics"] == {}


def test_short_text_returns_expected_shape():
    result = get_predictability_signal("Too short to judge reliably.")

    assert "score" in result
    assert "reason" in result
    assert "metrics" in result
    assert 0.0 <= result["score"] <= 1.0
    assert "word_count" in result["metrics"]


def test_formulaic_text_scores_higher_than_casual_text():
    formulaic_result = get_predictability_signal(FORMULAIC_TEXT)
    casual_result = get_predictability_signal(CASUAL_TEXT)

    assert "score" in formulaic_result
    assert "reason" in formulaic_result
    assert "metrics" in formulaic_result
    assert 0.0 <= formulaic_result["score"] <= 1.0
    assert formulaic_result["score"] > casual_result["score"]
