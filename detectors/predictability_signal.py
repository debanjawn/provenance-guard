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
ASSISTANT_PREAMBLES = [
    "certainly!",
    "certainly,",
    "here is a polished and professional response",
    "here's a polished and professional response",
    "here is a clear and concise response",
    "here's a clear and concise response",
]
CORPORATE_FORMULAIC_PHRASES = [
    "in today's rapidly evolving digital landscape",
    "it is important to note",
    "by leveraging",
    "cutting-edge technologies",
    "streamline workflows",
    "drive meaningful outcomes",
    "unlock new opportunities",
    "enhance productivity",
    "long-term success",
    "not as a replacement for human creativity",
    "powerful assistant",
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
TRANSITION_START_PATTERN = re.compile(
    r"(?:^|[.!?]\s+)(however|therefore|moreover|furthermore|in conclusion|in addition)\b",
    flags=re.IGNORECASE,
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _get_words(text: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", text.lower())


def _count_phrase_matches(text: str, phrases: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(phrase) for phrase in phrases)


def _count_unique_phrase_matches(text: str, phrases: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for phrase in phrases if phrase in lowered)


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

    repeated_word_total = sum(count - 1 for count in Counter(words).values() if count > 1)
    repetition_rate = repeated_word_total / len(words)

    transition_matches = _count_phrase_matches(lowered_text, COMMON_TRANSITIONS)
    transition_density = transition_matches / len(words)
    transition_start_matches = len(TRANSITION_START_PATTERN.findall(text))

    assistant_preamble_matches = _count_phrase_matches(lowered_text, ASSISTANT_PREAMBLES)
    corporate_phrase_matches = _count_phrase_matches(lowered_text, CORPORATE_FORMULAIC_PHRASES)

    unique_assistant_matches = _count_unique_phrase_matches(lowered_text, ASSISTANT_PREAMBLES)
    unique_corporate_matches = _count_unique_phrase_matches(
        lowered_text,
        CORPORATE_FORMULAIC_PHRASES,
    )
    unique_transition_matches = _count_unique_phrase_matches(lowered_text, COMMON_TRANSITIONS)
    unique_formulaic_matches = (
        unique_assistant_matches
        + unique_corporate_matches
        + unique_transition_matches
    )

    formulaic_category_count = sum(
        1
        for match_total in (
            assistant_preamble_matches,
            corporate_phrase_matches,
            transition_matches + transition_start_matches,
        )
        if match_total > 0
    )

    assistant_marker_score = _clamp((assistant_preamble_matches + unique_assistant_matches) / 2.0)
    corporate_phrase_score = _clamp(corporate_phrase_matches / 3.0)
    transition_density_score = _clamp(transition_density / 0.04)
    transition_structure_score = _clamp((transition_start_matches + transition_matches) / 3.0)
    repeated_phrase_score = _clamp(repeated_phrase_rate / 0.10)
    repetition_score = _clamp(repetition_rate / 0.22)
    formulaic_cluster_score = _clamp(
        (0.55 * (formulaic_category_count / 3.0))
        + (0.45 * _clamp(unique_formulaic_matches / 4.0))
    )

    score = _clamp(
        (0.28 * assistant_marker_score)
        + (0.22 * corporate_phrase_score)
        + (0.20 * formulaic_cluster_score)
        + (0.12 * transition_density_score)
        + (0.08 * transition_structure_score)
        + (0.05 * repeated_phrase_score)
        + (0.05 * repetition_score)
    )

    metrics = {
        "repeated_phrase_rate": round(repeated_phrase_rate, 4),
        "repetition_rate": round(repetition_rate, 4),
        "transition_phrase_matches": transition_matches,
        "transition_density": round(transition_density, 4),
        "transition_start_matches": transition_start_matches,
        "assistant_preamble_matches": assistant_preamble_matches,
        "corporate_phrase_matches": corporate_phrase_matches,
        "unique_formulaic_matches": unique_formulaic_matches,
        "formulaic_category_count": formulaic_category_count,
    }

    if score >= 0.75:
        reason = (
            "The text clusters assistant-style preambles, generic transitions, and corporate phrasing in a strongly formulaic pattern."
        )
    elif score >= 0.45:
        reason = "The text shows some predictable template language, but the evidence is mixed."
    else:
        reason = "The text does not show strong clustered assistant-style or formulaic phrasing."

    return {
        "score": round(score, 4),
        "reason": reason,
        "metrics": metrics,
    }
