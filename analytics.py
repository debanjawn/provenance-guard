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
    average_confidence = (
        round(sum(confidence_values) / len(confidence_values), 4)
        if confidence_values else 0.0
    )
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
    }
