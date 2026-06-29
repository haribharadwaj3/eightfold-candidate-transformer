import json
import os
from pipeline.extractors import BaseExtractor

class ATSJSONExtractor(BaseExtractor):
    def extract(self) -> list:
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"JSON file not found: {self.source_path}")
            
        with open(self.source_path, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Standardize single object to array of objects
        if isinstance(data, dict):
            raw_candidates = [data]
        elif isinstance(data, list):
            raw_candidates = data
        else:
            raise ValueError("ATS JSON must be an object or a list of objects")
            
        candidates = []
        for index, raw_item in enumerate(raw_candidates):
            # Normalization mapping heuristics
            normalized = self._map_to_canonical_fields(raw_item)
            
            candidates.append({
                "source_id": f"{os.path.basename(self.source_path)}#{index}",
                "source_type": "ats_json",
                "raw_fields": normalized,
                "confidence": 0.80
            })
            
        return candidates

    def _map_to_canonical_fields(self, item: dict) -> dict:
        """
        Uses heuristic key matching to map custom ATS keys to standard intermediate fields.
        """
        result = {
            "full_name": None,
            "emails": [],
            "phones": [],
            "location": {
                "city": None,
                "region": None,
                "country": None
            },
            "links": {
                "linkedin": None,
                "github": None,
                "portfolio": None,
                "other": []
            },
            "headline": None,
            "years_experience": None,
            "skills": [],
            "experience": [],
            "education": []
        }
        
        # Helper to search for keys case-insensitively
        def get_value_by_patterns(d, patterns):
            for k, v in d.items():
                k_lower = k.lower().replace("_", "").replace("-", "")
                for pattern in patterns:
                    if pattern in k_lower:
                        return v
            return None

        # 1. Full Name
        name_val = get_value_by_patterns(item, ["fullname", "candidatename", "applicantname", "name"])
        if isinstance(name_val, str):
            result["full_name"] = name_val
        elif isinstance(name_val, dict):
            # Maybe {"first": "Priya", "last": "Sharma"}
            first = get_value_by_patterns(name_val, ["first", "given"]) or ""
            last = get_value_by_patterns(name_val, ["last", "family", "surname"]) or ""
            result["full_name"] = f"{first} {last}".strip()

        # 2. Email
        email_val = get_value_by_patterns(item, ["email", "mail", "contactemail"])
        if isinstance(email_val, str):
            result["emails"] = [email_val]
        elif isinstance(email_val, list):
            result["emails"] = email_val

        # 3. Phone
        phone_val = get_value_by_patterns(item, ["phone", "cell", "mobile", "telephone", "contactnumber"])
        if isinstance(phone_val, str):
            result["phones"] = [phone_val]
        elif isinstance(phone_val, list):
            result["phones"] = phone_val

        # 4. Location
        loc_val = get_value_by_patterns(item, ["location", "address", "geo"])
        if isinstance(loc_val, dict):
            result["location"]["city"] = get_value_by_patterns(loc_val, ["city", "town"])
            result["location"]["region"] = get_value_by_patterns(loc_val, ["region", "state", "province"])
            result["location"]["country"] = get_value_by_patterns(loc_val, ["country", "nation"])
        elif isinstance(loc_val, str):
            # Parse string location like "San Francisco, CA, US"
            parts = [p.strip() for p in loc_val.split(",")]
            if len(parts) == 1:
                result["location"]["city"] = parts[0]
            elif len(parts) == 2:
                result["location"]["city"] = parts[0]
                result["location"]["country"] = parts[1]
            elif len(parts) >= 3:
                result["location"]["city"] = parts[0]
                result["location"]["region"] = parts[1]
                result["location"]["country"] = parts[2]

        # 5. Links / Socials
        links_val = get_value_by_patterns(item, ["links", "socials", "websites", "urls"])
        if isinstance(links_val, dict):
            result["links"]["linkedin"] = get_value_by_patterns(links_val, ["linkedin"])
            result["links"]["github"] = get_value_by_patterns(links_val, ["github"])
            result["links"]["portfolio"] = get_value_by_patterns(links_val, ["portfolio", "website", "blog"])
            other_val = get_value_by_patterns(links_val, ["other", "additional"])
            if isinstance(other_val, list):
                result["links"]["other"] = other_val
        elif isinstance(links_val, list):
            for link in links_val:
                if "linkedin.com" in link:
                    result["links"]["linkedin"] = link
                elif "github.com" in link:
                    result["links"]["github"] = link
                else:
                    result["links"]["other"].append(link)

        # 6. Headline / Job Title
        headline_val = get_value_by_patterns(item, ["headline", "title", "role", "designation", "summary"])
        if isinstance(headline_val, str):
            result["headline"] = headline_val

        # 7. Years of Experience
        years_val = get_value_by_patterns(item, ["yearsexperience", "experienceyears", "yoe"])
        if years_val is not None:
            try:
                result["years_experience"] = float(years_val)
            except (ValueError, TypeError):
                pass

        # 8. Skills
        skills_val = get_value_by_patterns(item, ["skills", "technologies", "expertise", "keywords"])
        if isinstance(skills_val, list):
            # Check if list of strings or list of objects
            for skill in skills_val:
                if isinstance(skill, str):
                    result["skills"].append({"name": skill, "confidence": 1.0, "sources": []})
                elif isinstance(skill, dict):
                    name = get_value_by_patterns(skill, ["name", "skill"])
                    conf = get_value_by_patterns(skill, ["confidence", "score", "level"])
                    if name:
                        # Normalize skill level if float or string
                        c_val = 1.0
                        if conf is not None:
                            try:
                                c_val = float(conf)
                                if c_val > 1.0: # e.g. out of 5 or 10
                                    c_val = c_val / 5.0 if c_val <= 5.0 else c_val / 10.0
                            except (ValueError, TypeError):
                                pass
                        result["skills"].append({"name": name, "confidence": c_val, "sources": []})
        elif isinstance(skills_val, str):
            # Comma separated
            for s in skills_val.split(","):
                if s.strip():
                    result["skills"].append({"name": s.strip(), "confidence": 1.0, "sources": []})

        # 9. Experience List
        exp_val = get_value_by_patterns(item, ["experience", "workhistory", "jobs", "employment"])
        if isinstance(exp_val, list):
            for work in exp_val:
                if isinstance(work, dict):
                    result["experience"].append({
                        "company": get_value_by_patterns(work, ["company", "employer"]) or "Unknown",
                        "title": get_value_by_patterns(work, ["title", "role", "position"]) or "Employee",
                        "start": get_value_by_patterns(work, ["start", "from"]),
                        "end": get_value_by_patterns(work, ["end", "to"]) or "Present",
                        "summary": get_value_by_patterns(work, ["summary", "description", "details"])
                    })

        # 10. Education List
        edu_val = get_value_by_patterns(item, ["education", "academic", "schools", "degrees"])
        if isinstance(edu_val, list):
            for school in edu_val:
                if isinstance(school, dict):
                    end_yr = get_value_by_patterns(school, ["endyear", "year", "graduationyear"])
                    try:
                        end_yr = int(end_yr) if end_yr is not None else None
                    except (ValueError, TypeError):
                        end_yr = None
                        
                    result["education"].append({
                        "institution": get_value_by_patterns(school, ["institution", "school", "university", "college"]) or "Unknown",
                        "degree": get_value_by_patterns(school, ["degree", "qualification"]),
                        "field": get_value_by_patterns(school, ["field", "major", "subject"]),
                        "end_year": end_yr
                    })

        return result
