import re
from pipeline.normalize import normalize_phone, normalize_skill

def resolve_json_path(record: dict, path: str):
    """
    Simple JSONPath resolver.
    Supports:
      - 'field' -> record['field']
      - 'field[0]' -> record['field'][0]
      - 'field[].subfield' -> [item['subfield'] for item in record['field']]
    """
    if not path:
        return None
        
    # Check for 'field[].subfield' pattern
    list_subfield_match = re.match(r'^(\w+)\[\]\.(\w+)$', path)
    if list_subfield_match:
        list_key, sub_key = list_subfield_match.groups()
        items = record.get(list_key, [])
        if isinstance(items, list):
            return [item.get(sub_key) for item in items if isinstance(item, dict) and sub_key in item]
        return []
        
    # Check for 'field[index]' pattern
    list_index_match = re.match(r'^(\w+)\[(\d+)\]$', path)
    if list_index_match:
        list_key, index_str = list_index_match.groups()
        index = int(index_str)
        items = record.get(list_key, [])
        if isinstance(items, list) and len(items) > index:
            return items[index]
        return None
        
    # Direct field access
    return record.get(path)

def project_candidate(record: dict, config: dict) -> dict:
    """
    Projects a canonical candidate profile into a custom schema based on configuration.
    """
    projected = {}
    on_missing = config.get("on_missing", "null") # "null", "omit", "error"
    
    # Process specified fields
    fields_config = config.get("fields", [])
    for field in fields_config:
        target_path = field.get("path")
        source_path = field.get("from", target_path)
        field_type = field.get("type", "string")
        is_required = field.get("required", False)
        norm_override = field.get("normalize")
        
        # Resolve value
        val = resolve_json_path(record, source_path)
        
        # Apply normalization overrides if requested
        if val is not None:
            if norm_override == "E164":
                if isinstance(val, list):
                    val = [normalize_phone(v)[0] for v in val]
                else:
                    val = normalize_phone(val)[0]
            elif norm_override == "canonical":
                if isinstance(val, list):
                    val = [normalize_skill(v)[0] for v in val]
                else:
                    val = normalize_skill(val)[0]
                    
        # Handle missing value
        if val is None or (isinstance(val, list) and not val):
            if is_required:
                if on_missing == "error":
                    raise ValueError(f"Required field '{target_path}' is missing or empty in candidate {record.get('candidate_id')}")
                elif on_missing == "omit":
                    continue
                else: # "null"
                    val = None
            else:
                if on_missing == "omit":
                    continue
                else: # "null"
                    val = None
                    
        # Type coercion/formatting check
        if val is not None:
            if field_type == "string" and not isinstance(val, str):
                val = str(val)
            elif field_type == "array" and not isinstance(val, list):
                val = [val]
                
        projected[target_path] = val

    # Toggle confidence/provenance if requested
    if config.get("include_confidence", True):
        if "overall_confidence" in record:
            projected["overall_confidence"] = record["overall_confidence"]
            
        # If skills is projected, check if it's projected as an object with confidence
        # or list of strings. If list of strings, confidence is already dropped.
        # But if it's custom projected, we can also attach provenance if required:
        if config.get("include_provenance", False) and "provenance" in record:
            projected["provenance"] = record["provenance"]
    else:
        # Explicitly remove confidence values
        if "overall_confidence" in projected:
            del projected["overall_confidence"]
            
    # Include provenance if explicitly enabled
    if config.get("include_provenance", False) and "provenance" in record:
        projected["provenance"] = record["provenance"]
        
    return projected

def project_profiles(records: list, config: dict = None) -> list:
    if not config:
        return records # Return default schema unchanged
    return [project_candidate(rec, config) for rec in records]
