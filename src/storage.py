import json
import threading
from pathlib import Path
from typing import Any, Dict


class JsonKVStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> Dict[str, Any]:
        with self._lock:
            raw = self.path.read_text(encoding="utf-8")
            try:
                return json.loads(raw or "{}")
            except json.JSONDecodeError:
                return {}

    def _save(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        self._save(data)


