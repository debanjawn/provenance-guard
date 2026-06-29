from labels import (
    LIKELY_AI_LABEL,
    LIKELY_HUMAN_LABEL,
    UNCERTAIN_LABEL,
    generate_label,
)


def test_likely_human_label_text():
    assert generate_label("likely_human", 0.2) == LIKELY_HUMAN_LABEL


def test_uncertain_label_text():
    assert generate_label("uncertain", 0.5) == UNCERTAIN_LABEL


def test_likely_ai_label_text():
    assert generate_label("likely_ai", 0.9) == LIKELY_AI_LABEL


def test_unknown_attribution_falls_back_to_uncertain():
    assert generate_label("something_else", 0.1) == UNCERTAIN_LABEL
