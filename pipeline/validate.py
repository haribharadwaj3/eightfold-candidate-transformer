import json
import os
import re

# Load default schema
DEFAULT_SCHEMA = {}
schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'default_schema.json')
if os.path.exists(schema_path):
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            DEFAULT_SCHEMA = json.load(f)
    except Exception as e:
        print(f"[Warning] Failed to load default schema config: {e}")

def validate_against_schema(data: dict, schema: dict = None) -> dict:
    """
    Validates a candidate profile dict against a JSON schema.
    If jsonschema library is missing, runs a robust fallback regex/type validator.
    """
    target_schema = schema if schema is not None else DEFAULT_SCHEMA
    
    try:
        import jsonschema
        # Perform validation using jsonschema package
        jsonschema.validate(instance=data, schema=target_schema)
        return {"valid": True, "errors": []}
    except ImportError:
        # Fallback manual validator if jsonschema is not installed
        return fallback_validate(data, target_schema)
    except Exception as e:
        # Capture schema errors
        return {"valid": False, "errors": [str(e)]}

def fallback_validate(data: dict, schema: dict) -> dict:
    """
    Pure Python validation fallback to ensure zero runtime dependencies during test execution.
    """
    errors = []
    
    # 1. Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Required field '{field}' is missing.")
            
    # 2. Check types & formats for main fields
    for field, val in data.items():
        if val is None:
            continue
            
        # Validate phones (E.164)
        if field == "phones" and isinstance(val, list):
            for phone in val:
                if not re.match(r'^\+[1-9]\d{1,14}$', str(phone)):
                    errors.append(f"Phone number '{phone}' must be E.164 format (e.g. +1234567890).")
                    
        # Validate emails
        if field == "emails" and isinstance(val, list):
            for email in val:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(email)):
                    errors.append(f"Email '{email}' is invalid.")
                    
        # Validate location
        if field == "location" and isinstance(val, dict):
            country = val.get("country")
            if country and not re.match(r'^[A-Z]{2}$', str(country)):
                errors.append(f"Location country code '{country}' must be ISO-3166 alpha-2 format.")
                
        # Validate experience dates
        if field == "experience" and isinstance(val, list):
            for i, job in enumerate(val):
                if not isinstance(job, dict):
                    continue
                start = job.get("start")
                end = job.get("end")
                if start and not re.match(r'^\d{4}-\d{2}$', str(start)):
                    errors.append(f"Experience[{i}] start date '{start}' must be YYYY-MM format.")
                if end and not re.match(r'^(\d{4}-\d{2}|Present)$', str(end)):
                    errors.append(f"Experience[{i}] end date '{end}' must be YYYY-MM or 'Present'.")
                    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def validate_profiles(profiles: list, schema: dict = None) -> list:
    """
    Validates a list of profiles. Returns a list of validation reports.
    """
    reports = []
    for profile in profiles:
        cand_id = profile.get("candidate_id", "unknown")
        report = validate_against_schema(profile, schema)
        reports.append({
            "candidate_id": cand_id,
            "valid": report["valid"],
            "errors": report["errors"]
        })
    return reports
