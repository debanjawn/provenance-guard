from detectors.predictability_signal import get_predictability_signal


OBVIOUS_AI_TEMPLATE_TEXT = (
    "Certainly! Here is a polished and professional response: "
    "In today's rapidly evolving digital landscape, artificial intelligence has become an essential tool for teams "
    "that want to streamline workflows, enhance productivity, and drive meaningful outcomes. "
    "Furthermore, organizations can unlock new opportunities by leveraging cutting-edge technologies as a powerful assistant, "
    "not as a replacement for human creativity. "
    "In conclusion, this approach supports long-term success."
)

MIXED_POLISHED_HUMAN_TEXT = (
    "I drafted this note for our neighborhood volunteer group after work and cleaned it up before sending it out. "
    "It is important to note that we should bring extra water if the weather stays hot, and furthermore, the sign-up sheet "
    "helps us avoid duplicate errands. The message is polished, but it still comes from a specific lived plan for Saturday."
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


def test_obvious_ai_template_text_scores_high():
    result = get_predictability_signal(OBVIOUS_AI_TEMPLATE_TEXT)

    assert result["score"] >= 0.75
    assert result["metrics"]["assistant_preamble_matches"] >= 1
    assert result["metrics"]["corporate_phrase_matches"] >= 4
    assert result["metrics"]["formulaic_category_count"] >= 3


def test_casual_human_text_stays_low():
    result = get_predictability_signal(CASUAL_TEXT)

    assert result["score"] < 0.35
    assert result["metrics"]["corporate_phrase_matches"] == 0
    assert result["metrics"]["assistant_preamble_matches"] == 0


def test_mixed_polished_human_text_stays_below_high_ai_range():
    result = get_predictability_signal(MIXED_POLISHED_HUMAN_TEXT)

    assert result["score"] < 0.75
    assert result["score"] > get_predictability_signal(CASUAL_TEXT)["score"]
