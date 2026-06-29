import os
import re
from pipeline.extractors import BaseExtractor

class ResumeExtractor(BaseExtractor):
    def extract(self) -> list:
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"Resume file not found: {self.source_path}")
            
        _, ext = os.path.splitext(self.source_path.lower())
        text = ""
        
        try:
            if ext == '.pdf':
                text = self._extract_pdf_text()
            elif ext == '.docx':
                text = self._extract_docx_text()
            else:
                # Treat as plain text
                with open(self.source_path, mode='r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
        except Exception as e:
            print(f"[Warning] Failed to extract text from resume {self.source_path}: {e}")
            # Try plain text fallback if pdf/docx parsing failed but file is readable as text
            try:
                with open(self.source_path, mode='r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except Exception:
                text = ""

        if not text.strip():
            print(f"[Warning] Empty text extracted from resume: {self.source_path}")
            return []

        raw_fields = self._parse_resume_text(text)
        
        return [{
            "source_id": os.path.basename(self.source_path),
            "source_type": "resume",
            "raw_fields": raw_fields,
            "confidence": 0.70
        }]

    def _extract_pdf_text(self) -> str:
        try:
            import pdfplumber
        except ImportError:
            print("[Warning] pdfplumber is not installed. PDF extraction will degrade.")
            return ""
            
        text_parts = []
        with pdfplumber.open(self.source_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_docx_text(self) -> str:
        try:
            import docx
        except ImportError:
            print("[Warning] python-docx is not installed. DOCX extraction will degrade.")
            return ""
            
        doc = docx.Document(self.source_path)
        text_parts = [paragraph.text for paragraph in doc.paragraphs]
        return "\n".join(text_parts)

    def _parse_resume_text(self, text: str) -> dict:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Full name: Heuristic - first non-empty line (usually the candidate's name)
        full_name = None
        if lines:
            # Avoid picking lines that look like section titles, emails, or urls
            for line in lines[:5]:
                if len(line) < 50 and not any(kw in line.lower() for kw in ["resume", "curriculum", "email", "phone", "contact", "http", "@"]):
                    full_name = line
                    break
            if not full_name:
                full_name = lines[0]

        # 2. Emails: standard regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        emails = list(set(re.findall(email_pattern, text)))

        # 3. Phones: standard international/local pattern
        phone_pattern = r'\+?\(?\d{1,4}\)?[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3}[-.\s]?\d{4,6}'
        phones = list(set(re.findall(phone_pattern, text)))

        # 4. Links: search for linkedin, github, portfolio
        links = {
            "linkedin": None,
            "github": None,
            "portfolio": None,
            "other": []
        }
        url_pattern = r'https?://[^\s\)]+'
        urls = re.findall(url_pattern, text)
        for url in urls:
            url_lower = url.lower()
            if "linkedin.com" in url_lower:
                links["linkedin"] = url
            elif "github.com" in url_lower:
                links["github"] = url
            else:
                links["other"].append(url)

        # 5. Skills extraction using simple keyword scanner
        skills = []
        # Predefined checklist of popular skills to look for in text
        skill_keywords = [
            "python", "javascript", "typescript", "java", "c++", "c#", "rust", "golang", "ruby",
            "react", "angular", "vue", "node", "django", "flask", "fastapi", "spring boot",
            "docker", "kubernetes", "aws", "gcp", "azure", "postgresql", "mongodb", "mysql", "redis",
            "machine learning", "deep learning", "nlp", "computer vision", "git", "ci/cd", "html", "css"
        ]
        
        text_lower = text.lower()
        for kw in skill_keywords:
            # Match boundary word to avoid substrings like "go" inside "good"
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text_lower):
                skills.append({
                    "name": kw,
                    "confidence": 0.8,
                    "sources": []
                })

        # 6. Experience & Education heuristic parsing
        experience = []
        education = []
        
        # Simple rule-based parser for sections
        current_section = None
        exp_keywords = ["experience", "work history", "employment", "professional history"]
        edu_keywords = ["education", "academic", "university", "college", "studies"]
        
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in exp_keywords) and len(line) < 30:
                current_section = "experience"
                continue
            elif any(kw in line_lower for kw in edu_keywords) and len(line) < 30:
                current_section = "education"
                continue
            elif len(line) < 30 and any(kw in line_lower for kw in ["skills", "interests", "projects"]):
                current_section = None
                continue
                
            if current_section == "experience":
                # Look for format: Company - Title (Date)
                # Or just split by delimiter
                parts = re.split(r'[-–|]', line)
                if len(parts) >= 2:
                    comp = parts[0].strip()
                    title = parts[1].strip()
                    # Look for dates in the line
                    date_match = re.search(r'\b(19|20)\d{2}\b', line)
                    start_val = f"{date_match.group()}-01" if date_match else None
                    experience.append({
                        "company": comp,
                        "title": title,
                        "start": start_val,
                        "end": "Present" if "present" in line_lower or "current" in line_lower else start_val,
                        "summary": line
                    })
            elif current_section == "education":
                # Look for format: University, Degree
                parts = re.split(r'[,–-]', line)
                if len(parts) >= 1:
                    inst = parts[0].strip()
                    deg = parts[1].strip() if len(parts) > 1 else None
                    year_match = re.search(r'\b(19|20)\d{2}\b', line)
                    end_yr = int(year_match.group()) if year_match else None
                    education.append({
                        "institution": inst,
                        "degree": deg,
                        "field": None,
                        "end_year": end_yr
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
            "links": links,
            "headline": None,
            "years_experience": None,
            "skills": skills,
            "experience": experience,
            "education": education
        }
