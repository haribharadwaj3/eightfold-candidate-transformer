from pipeline.merge import resolve_and_merge, records_match

def test_records_match():
    # Overlapping email
    rec1 = {"raw_fields": {"full_name": "Priya Sharma", "emails": ["priya@example.com"], "phones": []}}
    rec2 = {"raw_fields": {"full_name": "P. Sharma", "emails": ["priya@example.com"], "phones": []}}
    assert records_match(rec1["raw_fields"], rec2["raw_fields"]) is True

    # High similarity name match
    rec3 = {"raw_fields": {"full_name": "Priya Sharma", "emails": [], "phones": []}}
    rec4 = {"raw_fields": {"full_name": "Priya Sharm", "emails": [], "phones": []}}
    assert records_match(rec3["raw_fields"], rec4["raw_fields"]) is True

    # Non-match
    rec5 = {"raw_fields": {"full_name": "Rahul Kumar", "emails": [], "phones": []}}
    assert records_match(rec3["raw_fields"], rec5["raw_fields"]) is False

def test_resolve_and_merge():
    records = [
        {
            "source_id": "export.csv",
            "source_type": "csv",
            "raw_fields": {
                "full_name": "Priya Sharma",
                "emails": ["priya@example.com"],
                "phones": ["555-014-2323"]
            },
            "confidence": 0.85
        },
        {
            "source_id": "ats.json",
            "source_type": "ats_json",
            "raw_fields": {
                "full_name": "P. Sharma",
                "emails": ["priya@example.com"],
                "skills": ["python", "js"]
            },
            "confidence": 0.80
        }
    ]
    
    merged = resolve_and_merge(records)
    assert len(merged) == 1
    profile = merged[0]
    assert profile["full_name"] == "Priya Sharma"
    assert "priya@example.com" in profile["emails"]
    assert "+15550142323" in profile["phones"]
    # Check that skills got canonicalized and merged
    skill_names = [s["name"] for s in profile["skills"]]
    assert "Python" in skill_names
    assert "JavaScript" in skill_names
