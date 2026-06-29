# Extractors package
class BaseExtractor:
    def __init__(self, source_path: str):
        self.source_path = source_path
        
    def extract(self) -> list:
        """
        Extracts candidate data from the source.
        Returns a list of dicts, where each dict has:
          - source_id: string
          - source_type: string
          - raw_fields: dict (arbitrary mapping)
          - confidence: float
        """
        raise NotImplementedError
