import os
import requests
from pipeline.extractors import BaseExtractor

class GitHubExtractor(BaseExtractor):
    def __init__(self, source_path: str, token: str = None):
        super().__init__(source_path)
        self.token = token
        self.username = self._parse_username(source_path)

    def _parse_username(self, path: str) -> str:
        if path.startswith("github:"):
            return path.split("github:")[-1].strip()
        if "github.com/" in path:
            # Parse from URL
            parts = path.rstrip("/").split("github.com/")
            if len(parts) > 1:
                return parts[1].split("/")[0].strip()
        return path.strip()

    def extract(self) -> list:
        if not self.username:
            print("[Warning] GitHub username not resolved from path:", self.source_path)
            return []
            
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
            
        print(f"[GitHub API] Fetching profile for username: {self.username}")
        
        try:
            # Fetch user profile
            profile_url = f"https://api.github.com/users/{self.username}"
            r = requests.get(profile_url, headers=headers, timeout=5)
            
            if r.status_code == 404:
                print(f"[Warning] GitHub user '{self.username}' not found (404).")
                return []
            elif r.status_code == 403:
                # Rate limit exceeded
                print(f"[Warning] GitHub API rate limit exceeded or forbidden. Status 403.")
                return []
            r.raise_for_status()
            user_data = r.json()
            
            # Fetch top repositories to extract languages
            repos_url = f"https://api.github.com/users/{self.username}/repos?sort=pushed&per_page=15"
            repos_r = requests.get(repos_url, headers=headers, timeout=5)
            repos = []
            if repos_r.status_code == 200:
                repos = repos_r.json()
            else:
                print(f"[Warning] Failed to fetch repos for '{self.username}'. Status: {repos_r.status_code}")
                
            raw_fields = self._parse_github_data(user_data, repos)
            
            return [{
                "source_id": f"github:{self.username}",
                "source_type": "github",
                "raw_fields": raw_fields,
                "confidence": 0.90
            }]
            
        except Exception as e:
            print(f"[Warning] GitHub API request failed for '{self.username}': {e}")
            # Return empty or return a skeleton with what we know from username
            return []

    def _parse_github_data(self, user: dict, repos: list) -> dict:
        # Extract languages from repos
        languages = set()
        for repo in repos:
            lang = repo.get("language")
            if lang:
                languages.add(lang)
                
        # Build skills list
        skills = [{"name": lang, "confidence": 0.9, "sources": []} for lang in languages]
        
        # Build experience from repos (mock github project experience)
        experience = []
        if repos:
            # We can summarize GitHub activity as experience or just leave it empty
            # to be filled by other sources. Let's add a general experience block.
            repo_count = len(repos)
            experience.append({
                "company": "GitHub Open Source",
                "title": "Open Source Contributor",
                "start": None,
                "end": "Present",
                "summary": f"Active contributor with {repo_count} public repositories. Primary languages: {', '.join(languages)}."
            })
            
        emails = []
        email = user.get("email")
        if email:
            emails.append(email)
            
        # Parse name
        full_name = user.get("name") or user.get("login") or ""
        
        # Location parsing helper
        loc_str = user.get("location") or ""
        location = {"city": None, "region": None, "country": None}
        if loc_str:
            parts = [p.strip() for p in loc_str.split(",")]
            if len(parts) == 1:
                location["city"] = parts[0]
            elif len(parts) == 2:
                location["city"] = parts[0]
                location["country"] = parts[1]
            elif len(parts) >= 3:
                location["city"] = parts[0]
                location["region"] = parts[1]
                location["country"] = parts[2]
                
        portfolio = user.get("blog") or None
        if portfolio and not portfolio.startswith("http"):
            portfolio = f"https://{portfolio}"
            
        return {
            "full_name": full_name,
            "emails": emails,
            "phones": [],
            "location": location,
            "links": {
                "linkedin": None,
                "github": user.get("html_url"),
                "portfolio": portfolio,
                "other": []
            },
            "headline": user.get("bio") or f"GitHub developer - {user.get('login')}",
            "years_experience": None,
            "skills": skills,
            "experience": experience,
            "education": []
        }
