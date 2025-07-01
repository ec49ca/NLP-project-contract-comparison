from .base import BaseStorage, StorageResponse
from typing import Dict, Any


class PendingToolGraphStorage(BaseStorage):
    def save_tool_graph(self, id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        response = self.read_storage(self.config['pendingPath'])
        if not response["success"] or response["data"] is None:
            return response

        data = response["data"]
        data[id] = entry

        return self.write_storage(self.config['pendingPath'], data)

    def get_tool_graph(self, id: str) -> Dict[str, Any]:
        response = self.read_storage(self.config['pendingPath'])
        if not response["success"] or response["data"] is None:
            return response

        data = response["data"]
        entry = data.get(id)

        if not entry:
            return {
                "success": False,
                "error": f"Tool graph {id} not found in pending storage"
            }

        return {
            "success": True,
            "data": entry
        }

    def get_all_tool_graphs(self) -> Dict[str, Any]:
        return self.read_storage(self.config['pendingPath'])

    def remove_tool_graph(self, id: str) -> Dict[str, Any]:
        response = self.read_storage(self.config['pendingPath'])
        if not response["success"] or response["data"] is None:
            return response

        data = response["data"]
        if id in data:
            del data[id]

        return self.write_storage(self.config['pendingPath'], data)
