import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional


class Artifact:
    __slots__ = ("id", "name", "type", "path", "metadata", "timestamp", "automation_id")

    def __init__(
        self,
        name: str,
        artifact_type: str,
        path: str = "",
        metadata: Optional[dict] = None,
        automation_id: str = "",
    ):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.type = artifact_type
        self.path = path
        self.metadata = metadata or {}
        self.timestamp = time.time()
        self.automation_id = automation_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "path": self.path,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "automation_id": self.automation_id,
        }


class ArtifactManager:
    def __init__(self, base_dir: Path = Path("data/artifacts")):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: list[Artifact] = []
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        artifact_type: str,
        path: str = "",
        metadata: Optional[dict] = None,
        automation_id: str = "",
    ) -> Artifact:
        artifact = Artifact(name, artifact_type, path, metadata, automation_id)
        with self._lock:
            self._artifacts.append(artifact)
        return artifact

    def save_file(
        self,
        name: str,
        content: bytes,
        automation_id: str = "",
        extension: str = "",
    ) -> Artifact:
        safe_name = name.replace(" ", "_").replace("/", "_")
        if extension and not safe_name.endswith(f".{extension}"):
            safe_name = f"{safe_name}.{extension}"

        file_path = self._base_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        file_path.write_bytes(content)

        return self.register(
            name=name,
            artifact_type="file",
            path=str(file_path),
            metadata={"size": len(content)},
            automation_id=automation_id,
        )

    def get_for_automation(self, automation_id: str) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self._artifacts if a.automation_id == automation_id]

    def get_all(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self._artifacts[-limit:]]

    def get_by_id(self, artifact_id: str) -> Optional[dict]:
        with self._lock:
            for a in self._artifacts:
                if a.id == artifact_id:
                    return a.to_dict()
        return None


artifact_manager = ArtifactManager()
