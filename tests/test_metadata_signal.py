from metadata_signal import analyze_metadata


def test_human_documented_metadata_returns_human_friendly_result():
    result = analyze_metadata(
        {
            "tool_used": "Photoshop",
            "declared_ai_assistance": False,
            "has_process_notes": True,
            "edit_history_available": True,
            "human_reviewed": True,
        }
    )

    assert result["metadata_attribution"] == "likely_human_process"
    assert result["provenance_score"] < 0.4
    assert "metadata_checks" in result


def test_ai_assisted_metadata_returns_ai_friendly_result():
    result = analyze_metadata(
        {
            "tool_used": "Midjourney",
            "declared_ai_assistance": True,
            "has_process_notes": False,
            "edit_history_available": False,
            "human_reviewed": False,
        }
    )

    assert result["metadata_attribution"] == "likely_ai_assisted"
    assert result["provenance_score"] >= 0.8
    assert result["metadata_checks"]["tool_flagged_as_ai"] is True


def test_metadata_result_includes_metadata_checks():
    result = analyze_metadata({"tool_used": "Photoshop"})

    assert "metadata_checks" in result
    assert "tool_used" in result["metadata_checks"]
