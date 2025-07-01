import os
import json
from typing import Any, Dict, Optional, TypedDict


# ====== Type Definitions ======
class StorageResponse(TypedDict, total=False):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


class StorageConfig(TypedDict):
    pendingPath: str
    approvedPath: str
    rejectedPath: str


AgentStorage = Dict[str, Any]


# ====== Base Storage Class ======
class BaseStorage:
    def __init__(self, config: StorageConfig):
        self.config = config
        self.ensure_storage_files()

    def ensure_storage_files(self) -> None:
        for file_path in [
            self.config["pendingPath"],
            self.config["approvedPath"],
            self.config["rejectedPath"]
        ]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2)

    def read_storage(self, file_path: str) -> StorageResponse:
        try:
            if not os.path.exists(file_path):
                return {"success": True, "data": {}}
            with open(file_path, "r", encoding="utf-8") as f:
                return {"success": True, "data": json.load(f)}
        except Exception as e:
            return {"success": False, "error": f"Failed to read storage file: {str(e)}"}

    def write_storage(self, file_path: str, data: Any) -> StorageResponse:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to write storage file: {str(e)}"}

    def move_agent(
        self, from_path: str, to_path: str, agent_name: str
    ) -> StorageResponse:
        try:
            from_response = self.read_storage(from_path)
            if not from_response["success"] or from_response.get("data") is None:
                return from_response

            from_data = from_response["data"]
            agent_data = from_data.get(agent_name)

            if not agent_data:
                return {"success": False, "error": f"Agent {agent_name} not found in source storage"}

            to_response = self.read_storage(to_path)
            if not to_response["success"] or to_response.get("data") is None:
                return to_response

            to_data = to_response["data"]

            to_data[agent_name] = agent_data
            del from_data[agent_name]

            write_to = self.write_storage(to_path, to_data)
            if not write_to["success"]:
                return write_to

            write_from = self.write_storage(from_path, from_data)
            if not write_from["success"]:
                return write_from

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to move agent: {str(e)}"}
