import os
import json
from typing import Any, Dict, Optional


class StorageResponse:
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


class BaseStorage:
    def __init__(self, config: Dict[str, str]):
        self.config = config

    def read_storage(self, file_path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(file_path):
                default_data = {}
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2)
                return StorageResponse(True, default_data).to_dict()

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return StorageResponse(True, data).to_dict()
        except Exception as e:
            return StorageResponse(False, error=f"Failed to read storage: {str(e)}").to_dict()

    def write_storage(self, file_path: str, data: Any) -> Dict[str, Any]:
        try:
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return StorageResponse(True).to_dict()
        except Exception as e:
            return StorageResponse(False, error=f"Failed to write storage: {str(e)}").to_dict()
