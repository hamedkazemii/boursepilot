import yaml
from pathlib import Path

class RoadmapManager:
    def __init__(self, roadmap_path="roadmap.yaml"):
        self.path = Path(roadmap_path)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            return {}
        with self.path.open("r") as f:
            return yaml.safe_load(f)

    def get_current_sprint(self):
        return self.data.get("current_sprint", "N/A")
