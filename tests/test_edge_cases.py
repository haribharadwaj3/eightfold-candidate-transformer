import pytest
import os
from pipeline.ingest import ingest_source
from pipeline.merge import resolve_and_merge

def test_empty_missing_sources():
    # If source is missing, ingest_source should catch exception and return empty
    res = ingest_source("non_existent_file.csv")
    assert res == []

def test_malformed_json(tmp_path):
    # Create malformed JSON file
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{ invalid json")
    
    # Ingesting bad JSON should degrade gracefully (return empty)
    res = ingest_source(str(bad_json))
    assert res == []

def test_missing_required_fields_handling():
    from pipeline.project import project_candidate
    canonical = {
        "candidate_id": "cand_123",
        "full_name": None
    }
    
    # Required field is missing, on_missing is error -> raise ValueError
    config_err = {
        "fields": [{"path": "name", "from": "full_name", "type": "string", "required": True}],
        "on_missing": "error"
    }
    with pytest.raises(ValueError):
        project_candidate(canonical, config_err)

    # Required field is missing, on_missing is omit -> omit from output
    config_omit = {
        "fields": [{"path": "name", "from": "full_name", "type": "string", "required": True}],
        "on_missing": "omit"
    }
    projected = project_candidate(canonical, config_omit)
    assert "name" not in projected
