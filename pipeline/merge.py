import uuid
import hashlib
import re
from difflib import SequenceMatcher
from pipeline.normalize import normalize_record


# Source priorities (highest value wins)
SOURCE_CONFIDENCE_SCORES = {
    "github": 0.90,
    "csv": 0.85,
    "ats_json": 0.80,
    "resume": 0.70,
    "notes": 0.60
}

def calculate_name_similarity(name1: str, name2: str) -> float:
    if not name1 or not name2:
        return 0.0
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

def records_match(rec1: dict, rec2: dict) -> bool:
    """
    Determines if two records belong to the same candidate.
    Handles raw records, raw fields, or normalized records.
    Matches by:
      - Any overlapping email address
      - Any overlapping phone number
      - High similarity name match (>= 0.85)
    """
    # Unwrap raw_fields or fields if they are wrapped in record metadata dicts
    fields1 = rec1
    if "raw_fields" in rec1:
        fields1 = rec1["raw_fields"]
    elif "fields" in rec1:
        fields1 = rec1["fields"]
        
    fields2 = rec2
    if "raw_fields" in rec2:
        fields2 = rec2["raw_fields"]
    elif "fields" in rec2:
        fields2 = rec2["fields"]
        
    # 1. Email overlap
    emails1 = {e.strip().lower() for e in fields1.get("emails", []) if e}
    emails2 = {e.strip().lower() for e in fields2.get("emails", []) if e}
    if emails1 & emails2:
        return True
        
    # 2. Phone overlap
    phones1 = {re.sub(r'\D', '', p) for p in fields1.get("phones", []) if p}
    phones2 = {re.sub(r'\D', '', p) for p in fields2.get("phones", []) if p}
    if phones1 & phones2:
        return True
        
    # 3. Name similarity
    name1 = fields1.get("full_name")
    name2 = fields2.get("full_name")
    if name1 and name2 and calculate_name_similarity(name1, name2) >= 0.85:
        return True
        
    return False


def merge_candidate_cluster(cluster: list) -> dict:
    """
    Merges a list of extracted source records for a single candidate.
    """
    # 1. Normalize all records in the cluster and retain metadata
    normalized_records = []
    for rec in cluster:
        norm_fields, prov_list = normalize_record(rec["raw_fields"])
        
        # Attach source metadata to each field provenance
        source_id = rec["source_id"]
        source_type = rec["source_type"]
        confidence = rec["confidence"]
        
        updated_prov = []
        for p in prov_list:
            updated_prov.append({
                "field": p["field"],
                "source": f"{source_type}:{source_id}",
                "method": p["method"]
            })
            
        normalized_records.append({
            "fields": norm_fields,
            "provenance": updated_prov,
            "source_type": source_type,
            "source_id": source_id,
            "confidence": confidence
        })
        
    # Sort normalized records by confidence (highest confidence first) so we can pick winners easily
    normalized_records.sort(key=lambda x: x["confidence"], reverse=True)
    
    # 2. Merge scalars (Highest confidence wins)
    primary = normalized_records[0]
    
    merged = {
        "full_name": primary["fields"]["full_name"],
        "headline": primary["fields"]["headline"],
        "years_experience": primary["fields"]["years_experience"],
        "location": primary["fields"]["location"],
        "links": primary["fields"]["links"],
        "emails": [],
        "phones": [],
        "skills": [],
        "experience": [],
        "education": [],
        "provenance": []
    }
    
    # Add provenance for fields from the primary winner
    for p in primary["provenance"]:
        if p["field"] in ["full_name", "headline", "years_experience", "location"] or p["field"].startswith("links."):
            merged["provenance"].append(p)
            
    # For other fields, pull from secondary records if primary is missing them
    for rec in normalized_records[1:]:
        if not merged["full_name"] and rec["fields"]["full_name"]:
            merged["full_name"] = rec["fields"]["full_name"]
            merged["provenance"].extend([p for p in rec["provenance"] if p["field"] == "full_name"])
            
        if not merged["headline"] and rec["fields"]["headline"]:
            merged["headline"] = rec["fields"]["headline"]
            merged["provenance"].extend([p for p in rec["provenance"] if p["field"] == "headline"])
            
        if merged["years_experience"] is None and rec["fields"]["years_experience"] is not None:
            merged["years_experience"] = rec["fields"]["years_experience"]
            merged["provenance"].extend([p for p in rec["provenance"] if p["field"] == "years_experience"])
            
        if (not merged["location"]["city"] and not merged["location"]["country"]) and (rec["fields"]["location"]["city"] or rec["fields"]["location"]["country"]):
            merged["location"] = rec["fields"]["location"]
            merged["provenance"].extend([p for p in rec["provenance"] if p["field"] == "location"])
            
        # Merge links if primary is missing them
        for k in ["linkedin", "github", "portfolio"]:
            if not merged["links"][k] and rec["fields"]["links"][k]:
                merged["links"][k] = rec["fields"]["links"][k]
                merged["provenance"].extend([p for p in rec["provenance"] if p["field"] == f"links.{k}"])

    # 3. Merge arrays (Union strategy)
    seen_emails = set()
    seen_phones = set()
    seen_skills = {} # skill_name -> {confidence, sources: set()}
    
    # Extract unique emails and phones across all records
    for rec in normalized_records:
        src = f"{rec['source_type']}:{rec['source_id']}"
        
        # Emails
        for email in rec["fields"]["emails"]:
            if email not in seen_emails:
                seen_emails.add(email)
                merged["emails"].append(email)
                merged["provenance"].append({
                    "field": "emails",
                    "source": src,
                    "method": "union_merge"
                })
                
        # Phones
        for phone in rec["fields"]["phones"]:
            if phone not in seen_phones:
                seen_phones.add(phone)
                merged["phones"].append(phone)
                merged["provenance"].append({
                    "field": "phones",
                    "source": src,
                    "method": "union_merge"
                })
                
        # Links other list
        for other_link in rec["fields"]["links"].get("other", []):
            if other_link not in merged["links"]["other"]:
                merged["links"]["other"].append(other_link)
                merged["provenance"].append({
                    "field": "links.other",
                    "source": src,
                    "method": "union_merge"
                })
                
        # Skills (aggregate and track source provenance)
        for skill in rec["fields"]["skills"]:
            name = skill["name"]
            conf = skill["confidence"] * rec["confidence"] # Scale skill conf by source conf
            if name not in seen_skills:
                seen_skills[name] = {
                    "confidence": conf,
                    "sources": {src}
                }
            else:
                # Retain the highest scaled confidence
                seen_skills[name]["confidence"] = max(seen_skills[name]["confidence"], conf)
                seen_skills[name]["sources"].add(src)
                
        # Experience (simple union, matching duplicate roles)
        for job in rec["fields"]["experience"]:
            # Check for duplicate job (same company and title)
            dup = False
            for existing in merged["experience"]:
                if (existing["company"].lower() == job["company"].lower() and 
                    existing["title"].lower() == job["title"].lower()):
                    dup = True
                    break
            if not dup:
                merged["experience"].append(job)
                merged["provenance"].append({
                    "field": f"experience:{job['company']}",
                    "source": src,
                    "method": "union_merge"
                })
                
        # Education (simple union, matching duplicate school)
        for edu in rec["fields"]["education"]:
            dup = False
            for existing in merged["education"]:
                if existing["institution"].lower() == edu["institution"].lower():
                    dup = True
                    break
            if not dup:
                merged["education"].append(edu)
                merged["provenance"].append({
                    "field": f"education:{edu['institution']}",
                    "source": src,
                    "method": "union_merge"
                })

    # Convert skills dictionary back to array of objects
    for name, data in seen_skills.items():
        merged["skills"].append({
            "name": name,
            "confidence": round(data["confidence"], 2),
            "sources": sorted(list(data["sources"]))
        })
        merged["provenance"].append({
            "field": f"skills:{name}",
            "source": ", ".join(sorted(list(data["sources"]))),
            "method": "aggregate_skills"
        })

    # Sort experience by end date / start date (most recent first)
    def parse_exp_date(date_str):
        if not date_str or date_str == "Present":
            return "9999-12"
        return date_str
    merged["experience"].sort(key=lambda x: parse_exp_date(x.get("end")), reverse=True)

    # 4. Generate stable candidate ID
    # Use MD5 of primary email, or if no email, use name
    if merged["emails"]:
        anchor = merged["emails"][0]
    else:
        anchor = merged["full_name"] or str(uuid.uuid4())
    hasher = hashlib.md5(anchor.encode('utf-8'))
    merged["candidate_id"] = f"cand_{hasher.hexdigest()[:16]}"
    
    # 5. Compute overall confidence
    # Overall confidence is computed as weighted average of source confidences
    # + completion penalty/bonus
    source_confs = [rec["confidence"] for rec in normalized_records]
    base_conf = sum(source_confs) / len(source_confs) if source_confs else 0.5
    
    # Completeness multiplier (based on fields filled)
    essential_fields = ["full_name", "emails", "phones", "skills", "experience"]
    filled_count = sum(1 for field in essential_fields if merged.get(field))
    completeness = filled_count / len(essential_fields)
    
    overall_conf = (base_conf * 0.7) + (completeness * 0.3)
    merged["overall_confidence"] = round(overall_conf, 2)
    
    return merged

def resolve_and_merge(extracted_records: list) -> list:
    """
    Resolves duplicates and merges candidates across multiple raw records.
    """
    clusters = []
    
    for rec in extracted_records:
        matched_cluster_index = -1
        for i, cluster in enumerate(clusters):
            # Check if record matches any existing candidate in the cluster
            if any(records_match(rec, existing) for existing in cluster):
                matched_cluster_index = i
                break
                
        if matched_cluster_index != -1:
            clusters[matched_cluster_index].append(rec)
        else:
            clusters.append([rec])
            
    # Merge each cluster into a single canonical candidate
    merged_profiles = []
    for cluster in clusters:
        profile = merge_candidate_cluster(cluster)
        merged_profiles.append(profile)
        
    return merged_profiles
