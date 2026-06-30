def _round_latency(value: float) -> int:
    return int(round(value))


def get_analytics(entries: list[dict]) -> dict:
    classified_entries = [
        entry for entry in entries
        if entry.get("status") == "classified"
    ]
    classified_with_attribution = [
        entry for entry in classified_entries
        if entry.get("attribution")
    ]

    total_submissions = len(classified_entries)
    likely_ai_count = sum(
        1 for entry in classified_with_attribution
        if entry.get("attribution") == "likely_ai"
    )
    likely_human_count = sum(
        1 for entry in classified_with_attribution
        if entry.get("attribution") == "likely_human"
    )
    uncertain_count = sum(
        1 for entry in classified_with_attribution
        if entry.get("attribution") == "uncertain"
    )

    appeal_count = sum(
        1 for entry in entries
        if entry.get("status") == "under_review"
    )

    confidence_values = [
        float(entry["confidence"])
        for entry in classified_entries
        if isinstance(entry.get("confidence"), (int, float))
    ]
    latency_entries = [
        entry for entry in classified_entries
        if isinstance(entry.get("llm_latency_ms"), (int, float))
    ]
    average_confidence = (
        round(sum(confidence_values) / len(confidence_values), 4)
        if confidence_values else 0.0
    )
    average_llm_latency_ms = (
        _round_latency(
            sum(float(entry["llm_latency_ms"]) for entry in latency_entries) / len(latency_entries)
        )
        if latency_entries else 0
    )
    latency_by_provider: dict[str, list[float]] = {}
    for entry in latency_entries:
        provider = entry.get("llm_provider")
        if isinstance(provider, str) and provider.strip():
            latency_by_provider.setdefault(provider, []).append(float(entry["llm_latency_ms"]))

    average_llm_latency_by_provider = {
        provider: _round_latency(sum(values) / len(values))
        for provider, values in latency_by_provider.items()
    }
    appeal_rate = (
        round(appeal_count / total_submissions, 4)
        if total_submissions else 0.0
    )

    return {
        "total_submissions": total_submissions,
        "likely_ai_count": likely_ai_count,
        "likely_human_count": likely_human_count,
        "uncertain_count": uncertain_count,
        "appeal_count": appeal_count,
        "appeal_rate": appeal_rate,
        "average_confidence": average_confidence,
        "average_llm_latency_ms": average_llm_latency_ms,
        "average_llm_latency_by_provider": average_llm_latency_by_provider,
    }
