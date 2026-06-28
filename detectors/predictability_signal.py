import re
from collections import Counter


MIN_WORD_COUNT = 20
COMMON_TRANSITIONS = [
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "in conclusion",
    "for example",
    "for instance",
    "on the other hand",
    "as a result",
    "in addition",
]
FORMULAIC_PHRASES = [
    "it is important to note",
    "in today's world",
    "plays a crucial role",
    "there are many factors",
    "there are several key factors",
    "in summary",
    "one of the most important",
    "this highlights the importance",
    "the purpose of this",
    "it can be argued that",
    "overall, it is clear",
    "it is essential to recognize",
    "leveraging innovative solutions",
]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _get_words(text: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", text.lower())


def _count_phrase_matches(text: str, phrases: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(phrase) for phrase in phrases)


def get_predictability_signal(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        return {
            "score": 0.5,
            "reason": "No usable text was provided, so the predictability result is uncertain.",
            "metrics": {},
        }

    words = _get_words(text)
    if len(words) < MIN_WORD_COUNT:
        return {
            "score": 0.5,
            "reason": "The text is too short for a reliable predictability judgment, so the result is uncertain.",
            "metrics": {
                "word_count": len(words),
            },
        }

    lowered_text = text.lower()
    bigrams = [" ".join(words[index:index + 2]) for index in range(len(words) - 1)]
    repeated_bigram_total = sum(
        count - 1 for count in Counter(bigrams).values() if count > 1
    )
    repeated_phrase_rate = repeated_bigram_total / max(len(bigrams), 1)

    transition_matches = _count_phrase_matches(lowered_text, COMMON_TRANSITIONS)
    transition_density = transition_matches / len(words)

    formulaic_phrase_matches = _count_phrase_matches(lowered_text, FORMULAIC_PHRASES)
    combined_formulaic_matches = transition_matches + formulaic_phrase_matches

    repeated_word_total = sum(count - 1 for count in Counter(words).values() if count > 1)
    repetition_rate = repeated_word_total / len(words)

    formulaic_intensity_score = _clamp(combined_formulaic_matches / 4.0)
    transition_density_score = _clamp(transition_density / 0.05)
    repeated_phrase_score = _clamp(repeated_phrase_rate / 0.10)
    repetition_score = _clamp(repetition_rate / 0.22)

    score = _clamp(
        (0.20 * repeated_phrase_score)
        + (0.20 * repetition_score)
        + (0.25 * transition_density_score)
        + (0.35 * formulaic_intensity_score)
    )

    metrics = {
        "repeated_phrase_rate": round(repeated_phrase_rate, 4),
        "transition_phrase_matches": transition_matches,
        "transition_density": round(transition_density, 4),
        "formulaic_phrase_matches": formulaic_phrase_matches,
        "combined_formulaic_matches": combined_formulaic_matches,
    }

    if score >= 0.7:
        reason = "The text uses repeated patterns and formulaic phrasing that look more predictable."
    elif score >= 0.4:
        reason = "The text shows some predictable phrasing, but the evidence is mixed."
    else:
        reason = "The text does not show strong formulaic or repetitive phrasing."

    return {
        "score": round(score, 4),
        "reason": reason,
        "metrics": metrics,
    }
