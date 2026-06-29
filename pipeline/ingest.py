import os
from pipeline.extractors.csv_extractor import CSVExtractor
from pipeline.extractors.ats_json_extractor import ATSJSONExtractor
from pipeline.extractors.github_extractor import GitHubExtractor
from pipeline.extractors.resume_extractor import ResumeExtractor
from pipeline.extractors.notes_extractor import NotesExtractor

def detect_source_type(path: str) -> str:
    path_lower = path.lower()
    if path_lower.startswith("github:") or "github.com" in path_lower:
        return "github"
    
    _, ext = os.path.splitext(path_lower)
    if ext == '.csv':
        return "csv"
    elif ext == '.json':
        return "ats_json"
    elif ext in ['.pdf', '.docx']:
        return "resume"
    elif ext in ['.txt', '.log']:
        if "notes" in path_lower:
            return "notes"
        return "resume" # Txt files can be parsed as text-based resumes too
    return "notes"

def ingest_source(path: str, github_token: str = None) -> list:
    """
    Detects source type and dispatches to the corresponding extractor.
    Returns a list of extracted candidate dicts.
    """
    source_type = detect_source_type(path)
    
    try:
        if source_type == "csv":
            extractor = CSVExtractor(path)
        elif source_type == "ats_json":
            extractor = ATSJSONExtractor(path)
        elif source_type == "github":
            extractor = GitHubExtractor(path, token=github_token)
        elif source_type == "resume":
            extractor = ResumeExtractor(path)
        elif source_type == "notes":
            extractor = NotesExtractor(path)
        else:
            print(f"[Warning] Unknown source type for path: {path}")
            return []
        
        return extractor.extract()
    except Exception as e:
        print(f"[Error] Failed to extract from {path} (type: {source_type}): {e}")
        return []
