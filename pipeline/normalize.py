import json
import os
import re
import pycountry
import phonenumbers
from dateutil import parser as date_parser

# Load skills synonyms if file exists
SKILLS_SYNONYMS = {}
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'skills_synonyms.json')
if os.path.exists(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            SKILLS_SYNONYMS = json.load(f)
    except Exception as e:
        print(f"[Warning] Failed to load skills synonyms: {e}")

def normalize_name(name: str) -> tuple:
    """
    Normalizes name to Title Case, stripping extra whitespace.
    Returns (normalized_value, method_description)
    """
    if not name or not isinstance(name, str):
        return None, "none"
    clean = re.sub(r'\s+', ' ', name).strip()
    return clean.title(), "title_case_strip"

def normalize_email(email: str) -> tuple:
    """
    Normalizes email to lowercase.
    Returns (normalized_value, method_description)
    """
    if not email or not isinstance(email, str):
        return None, "none"
    return email.strip().lower(), "lowercase_strip"

def normalize_phone(phone: str, default_region: str = "US") -> tuple:
    """
    Normalizes phone numbers to E.164 format using phonenumbers library.
    Returns (normalized_value, method_description)
    """
    if not phone or not isinstance(phone, str):
        return None, "none"
        
    clean_phone = phone.strip()
    try:
        parsed = phonenumbers.parse(clean_phone, default_region)
        if phonenumbers.is_valid_number(parsed):
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return e164, "phonenumbers_e164"
    except Exception:
        pass
        
    # Heuristic fallback if library parsing fails
    # Strip all non-digit chars except leading '+'
    has_plus = clean_phone.startswith('+')
    digits = re.sub(r'\D', '', clean_phone)
    if digits:
        if has_plus:
            return f"+{digits}", "regex_strip_with_plus"
        # If it looks like a US number without country code
        if len(digits) == 10:
            return f"+1{digits}", "regex_strip_us_default"
        # Return prefixing +
        return f"+{digits}", "regex_strip_fallback"
        
    return None, "none"

def normalize_date(date_str: str) -> tuple:
    """
    Normalizes dates to YYYY-MM format.
    Handles 'Present' or 'current' as 'Present'.
    Returns (normalized_value, method_description)
    """
    if not date_str or not isinstance(date_str, str):
        return None, "none"
        
    val = date_str.strip()
    if val.lower() in ["present", "current", "now"]:
        return "Present", "static_present"
        
    try:
        # Use dateutil parser
        parsed = date_parser.parse(val, fuzzy=True)
        return parsed.strftime("%Y-%m"), "dateutil_yyyy_mm"
    except Exception:
        pass
        
    # Heuristic fallback via regex
    # Match YYYY or YYYY/MM or MM/YYYY
    match_yyyy = re.search(r'\b(19|20)\d{2}\b', val)
    if match_yyyy:
        year = match_yyyy.group()
        # Look for month digit/name
        match_mm = re.search(r'\b(0?[1-9]|1[0-2])\b', val)
        month = match_mm.group().zfill(2) if match_mm else "01"
        return f"{year}-{month}", "regex_extract_yyyy_mm"
        
    return None, "none"

def normalize_skill(skill_name: str) -> tuple:
    """
    Normalizes skills using the synonym dictionary config.
    Returns (normalized_value, method_description)
    """
    if not skill_name or not isinstance(skill_name, str):
        return None, "none"
        
    clean = skill_name.strip().lower()
    
    # Check direct dictionary lookup
    if clean in SKILLS_SYNONYMS:
        return SKILLS_SYNONYMS[clean], "synonym_map"
        
    # Fallback: capitalize properly
    # If the skill name has special characters like c++, keep them, otherwise title case
    if len(clean) <= 3:
        return skill_name.strip().upper(), "uppercase_short_skill"
        
    return skill_name.strip().title(), "title_case_fallback"

def normalize_location(loc_dict: dict) -> tuple:
    """
    Normalizes location to {city, region, country} and validates country to ISO-3166 alpha-2.
    Returns (normalized_dict, method_description)
    """
    result = {
        "city": None,
        "region": None,
        "country": None
    }
    
    if not loc_dict or not isinstance(loc_dict, dict):
        return result, "none"
        
    city = loc_dict.get("city")
    region = loc_dict.get("region")
    country = loc_dict.get("country")
    
    result["city"] = city.strip() if city and isinstance(city, str) else None
    result["region"] = region.strip() if region and isinstance(region, str) else None
    
    if country and isinstance(country, str):
        country_clean = country.strip()
        
        # Check if already ISO alpha-2
        if len(country_clean) == 2 and country_clean.isalpha():
            result["country"] = country_clean.upper()
            return result, "direct_iso2"
            
        # Lookup country using pycountry
        try:
            matched = pycountry.countries.search_fuzzy(country_clean)
            if matched:
                result["country"] = matched[0].alpha_2
                return result, "pycountry_fuzzy_lookup"
        except Exception:
            pass
            
        # Default fallback
        result["country"] = country_clean[:2].upper()
        return result, "slice_fallback"
        
    return result, "partial_location"

def normalize_record(raw_fields: dict) -> dict:
    """
    Applies all normalizers to a raw candidate field structure.
    Returns a dict of normalized fields and a list of field provenance metadata.
    """
    normalized = {}
    provenance = []
    
    # Name
    norm_name, method = normalize_name(raw_fields.get("full_name"))
    normalized["full_name"] = norm_name
    if norm_name:
        provenance.append({"field": "full_name", "method": method})
        
    # Emails
    normalized["emails"] = []
    for email in raw_fields.get("emails", []):
        norm_email, method = normalize_email(email)
        if norm_email and norm_email not in normalized["emails"]:
            normalized["emails"].append(norm_email)
            provenance.append({"field": "emails", "method": method})
            
    # Phones
    normalized["phones"] = []
    for phone in raw_fields.get("phones", []):
        norm_phone, method = normalize_phone(phone)
        if norm_phone and norm_phone not in normalized["phones"]:
            normalized["phones"].append(norm_phone)
            provenance.append({"field": "phones", "method": method})
            
    # Location
    norm_loc, method = normalize_location(raw_fields.get("location"))
    normalized["location"] = norm_loc
    if norm_loc["city"] or norm_loc["country"]:
        provenance.append({"field": "location", "method": method})
        
    # Links
    links = raw_fields.get("links", {})
    normalized["links"] = {
        "linkedin": links.get("linkedin"),
        "github": links.get("github"),
        "portfolio": links.get("portfolio"),
        "other": links.get("other", [])
    }
    # Basic clean links
    for k in ["linkedin", "github", "portfolio"]:
        val = normalized["links"][k]
        if val:
            normalized["links"][k] = val.strip()
            provenance.append({"field": f"links.{k}", "method": "strip"})
            
    # Headline
    headline = raw_fields.get("headline")
    normalized["headline"] = headline.strip() if headline else None
    if normalized["headline"]:
        provenance.append({"field": "headline", "method": "strip"})
        
    # Years Experience
    normalized["years_experience"] = raw_fields.get("years_experience")
    if normalized["years_experience"] is not None:
        provenance.append({"field": "years_experience", "method": "passthrough"})
        
    # Skills
    normalized["skills"] = []
    for skill in raw_fields.get("skills", []):
        if isinstance(skill, dict):
            name = skill.get("name")
            conf = skill.get("confidence", 1.0)
        else:
            name = skill
            conf = 1.0
            
        norm_name, method = normalize_skill(name)
        if norm_name:
            normalized["skills"].append({
                "name": norm_name,
                "confidence": conf,
                "sources": [] # Set during merge
            })
            provenance.append({"field": f"skills:{norm_name}", "method": method})
            
    # Experience
    normalized["experience"] = []
    for job in raw_fields.get("experience", []):
        start_norm, start_m = normalize_date(job.get("start"))
        end_norm, end_m = normalize_date(job.get("end"))
        
        normalized["experience"].append({
            "company": job.get("company", "Unknown").strip(),
            "title": job.get("title", "Employee").strip(),
            "start": start_norm,
            "end": end_norm or "Present",
            "summary": job.get("summary", "").strip() if job.get("summary") else None
        })
        provenance.append({"field": "experience", "method": f"dates_normalized_{start_m}_{end_m}"})
        
    # Education
    normalized["education"] = []
    for edu in raw_fields.get("education", []):
        normalized["education"].append({
            "institution": edu.get("institution", "Unknown").strip(),
            "degree": edu.get("degree").strip() if edu.get("degree") else None,
            "field": edu.get("field").strip() if edu.get("field") else None,
            "end_year": edu.get("end_year")
        })
        provenance.append({"field": "education", "method": "strip"})
        
    return normalized, provenance
