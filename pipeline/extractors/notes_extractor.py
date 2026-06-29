import os
import re
from pipeline.extractors import BaseExtractor

class NotesExtractor(BaseExtractor):
    def extract(self) -> list:
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"Notes file not found: {self.source_path}")
            
        with open(self.source_path, mode='r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            
        raw_fields = self._parse_notes_text(text)
        
        return [{
            "source_id": os.path.basename(self.source_path),
            "source_type": "notes",
            "raw_fields": raw_fields,
            "confidence": 0.60
        }]

    def _parse_notes_text(self, text: str) -> dict:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Heuristics for notes extraction
        full_name = None
        emails = []
        phones = []
        skills = []
        headline = None
        years_experience = None
        experience = []
        education = []

        # Find emails and phones in text
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        emails = list(set(re.findall(email_pattern, text)))

        phone_pattern = r'\+?\(?\d{1,4}\)?[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3}[-.\s]?\d{4,6}'
        phones = list(set(re.findall(phone_pattern, text)))

        # Predefined skill matching keywords
        skill_keywords = [
            "python", "javascript", "typescript", "java", "c++", "c#", "rust", "golang", "ruby",
            "react", "angular", "vue", "node", "django", "flask", "fastapi", "spring boot",
            "docker", "kubernetes", "aws", "gcp", "azure", "postgresql", "mongodb", "mysql", "redis",
            "machine learning", "deep learning", "nlp", "computer vision", "git", "ci/cd", "html", "css"
        ]
        text_lower = text.lower()
        for kw in skill_keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text_lower):
                skills.append({
                    "name": kw,
                    "confidence": 0.6, # Low confidence from notes
                    "sources": []
                })

        # Scan line by line for labels like "Name:", "Phone:", "Skills:", "Experience:", "Yoe:"
        for line in lines:
            line_lower = line.lower()
            
            # Name pattern matching
            name_match = re.match(r'^(?:candidate\s+)?name\s*:\s*(.+)$', line, re.IGNORECASE)
            if name_match:
                full_name = name_match.group(1).strip()
                continue
                
            # Years experience pattern matching
            yoe_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:yrs|years?)\s*(?:of\s*)?experience', line_lower)
            if yoe_match:
                try:
                    years_experience = float(yoe_match.group(1))
                except ValueError:
                    pass
                continue
                
            # Check for current title
            title_match = re.match(r'^(?:current\s+)?(?:job\s+)?title\s*:\s*(.+)$', line, re.IGNORECASE)
            if title_match:
                headline = title_match.group(1).strip()
                continue
                
            # Heuristic for name if not found via "Name:" label:
            # Look at first line if it's brief and doesn't match labels
            if not full_name and len(line) < 30 and "notes" not in line_lower:
                # Basic check if it contains alphabets only
                if re.match(r'^[A-Za-z\s\.]+$', line):
                    full_name = line

        # If we have experience years but no detailed job, generate a skeleton experience record
        if years_experience and headline:
            experience.append({
                "company": "Current Employer",
                "title": headline,
                "start": None,
                "end": "Present",
                "summary": f"Identified in recruiter notes. Total experience estimated at {years_experience} years."
            })

        return {
            "full_name": full_name,
            "emails": emails,
            "phones": phones,
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
            "headline": headline,
            "years_experience": years_experience,
            "skills": skills,
            "experience": experience,
            "education": education
        }
