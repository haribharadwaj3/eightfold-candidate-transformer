import csv
import os
from pipeline.extractors import BaseExtractor

class CSVExtractor(BaseExtractor):
    def extract(self) -> list:
        candidates = []
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"CSV file not found: {self.source_path}")
            
        with open(self.source_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Standardize column headers to lowercase strip
            fieldnames = [field.strip().lower() for field in (reader.fieldnames or [])]
            
            # Map field names
            for row in reader:
                # Clean keys
                cleaned_row = {k.strip().lower(): v for k, v in row.items() if k is not None}
                
                # Extract values with fallback
                name = cleaned_row.get("name", cleaned_row.get("full_name", ""))
                email = cleaned_row.get("email", cleaned_row.get("emails", ""))
                phone = cleaned_row.get("phone", cleaned_row.get("phones", ""))
                current_company = cleaned_row.get("current_company", cleaned_row.get("company", ""))
                title = cleaned_row.get("title", cleaned_row.get("headline", ""))
                
                raw_fields = {
                    "full_name": name.strip() if name else None,
                    "emails": [email.strip()] if email and email.strip() else [],
                    "phones": [phone.strip()] if phone and phone.strip() else [],
                }
                
                if title and title.strip():
                    raw_fields["headline"] = title.strip()
                    
                if current_company and current_company.strip():
                    raw_fields["experience"] = [{
                        "company": current_company.strip(),
                        "title": title.strip() if title else "Employee",
                        "start": None,
                        "end": "Present",
                        "summary": "Current role"
                    }]
                else:
                    raw_fields["experience"] = []
                    
                candidates.append({
                    "source_id": os.path.basename(self.source_path),
                    "source_type": "csv",
                    "raw_fields": raw_fields,
                    "confidence": 0.85
                })
        return candidates
