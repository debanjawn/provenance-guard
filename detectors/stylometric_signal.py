import re
from collections import Counter


MIN_WORD_COUNT = 20


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _get_words(text: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", text.lower())


def _get_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def get_stylometric_signal(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        return {
            "score": 0.5,
            "reason": "No usable text was provided, so the stylometric result is uncertain.",
            "metrics": {},
        }

    words = _get_words(text)
    if len(words) < MIN_WORD_COUNT:
        return {
            "score": 0.5,
            "reason": "The text is too short for a reliable stylometric judgment, so the result is uncertain.",
            "metrics": {
                "word_count": len(words),
            },
        }

    sentences = _get_sentences(text)
    sentence_lengths = [len(_get_words(sentence)) for sentence in sentences] or [len(words)]
    sentence_length_variance = _variance(sentence_lengths)
    type_token_ratio = len(set(words)) / len(words)
    punctuation_count = len(re.findall(r"[,:;!?'\"]", text))
    punctuation_density = punctuation_count / max(len(text), 1)

    word_counts = Counter(words)
    repeated_word_total = sum(count - 1 for count in word_counts.values() if count > 1)
    repetition_rate = repeated_word_total / len(words)

    variance_score = 1.0 - _clamp(sentence_length_variance / 40.0)
    diversity_score = 1.0 - _clamp((type_token_ratio - 0.30) / 0.40)
    punctuation_score = 1.0 - _clamp(punctuation_density / 0.08)
    repetition_score = _clamp(repetition_rate / 0.25)

    score = _clamp(
        (0.35 * variance_score)
        + (0.30 * diversity_score)
        + (0.15 * punctuation_score)
        + (0.20 * repetition_score)
    )

    metrics = {
        "sentence_length_variance": round(sentence_length_variance, 4),
        "type_token_ratio": round(type_token_ratio, 4),
        "punctuation_density": round(punctuation_density, 4),
        "repetition_rate": round(repetition_rate, 4),
    }

    if score >= 0.7:
        reason = "The text looks relatively uniform in structure and word usage."
    elif score >= 0.4:
        reason = "The text shows mixed stylometric signals with some uniformity and some variation."
    else:
        reason = "The text shows more variation in structure and wording, which looks less AI-like."

    return {
        "score": round(score, 4),
        "reason": reason,
        "metrics": metrics,
    }
