from pipeline.project import project_candidate

def test_project_candidate():
    canonical = {
        "candidate_id": "cand_12345",
        "full_name": "Priya Sharma",
        "emails": ["priya@example.com", "priya.s@example.com"],
        "phones": ["+15550142323"],
        "skills": [
            {"name": "Python", "confidence": 0.9, "sources": []},
            {"name": "JavaScript", "confidence": 0.8, "sources": []}
        ],
        "overall_confidence": 0.85
    }
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "primary_email", "from": "emails[0]", "type": "string", "required": True },
            { "path": "skill_names", "from": "skills[].name", "type": "array" }
        ],
        "include_confidence": True,
        "on_missing": "null"
    }
    
    projected = project_candidate(canonical, config)
    assert projected["name"] == "Priya Sharma"
    assert projected["primary_email"] == "priya@example.com"
    assert projected["skill_names"] == ["Python", "JavaScript"]
    assert projected["overall_confidence"] == 0.85
