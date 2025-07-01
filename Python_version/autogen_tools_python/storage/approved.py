from typing import Any, Dict
from .base import BaseStorage, StorageResponse


class ApprovedStorage(BaseStorage):
    def save_agent(self, agent_name: str, agent_data: Any) -> StorageResponse:
        response = self.read_storage(self.config["approvedPath"])
        if not response["success"] or response.get("data") is None:
            return response

        data: Dict[str, Any] = response["data"]
        data[agent_name] = agent_data
        return self.write_storage(self.config["approvedPath"], data)

    def get_agent(self, agent_name: str) -> StorageResponse:
        response = self.read_storage(self.config["approvedPath"])
        if not response["success"] or response.get("data") is None:
            return response

        data: Dict[str, Any] = response["data"]
        agent = data.get(agent_name)

        if not agent:
            return {
                "success": False,
                "error": f"Agent {agent_name} not found in approved storage"
            }

        return {"success": True, "data": agent}

    def get_all_agents(self) -> StorageResponse:
        return self.read_storage(self.config["approvedPath"])

    def remove_agent(self, agent_name: str) -> StorageResponse:
        response = self.read_storage(self.config["approvedPath"])
        if not response["success"] or response.get("data") is None:
            return response

        data: Dict[str, Any] = response["data"]
        data.pop(agent_name, None)

        return self.write_storage(self.config["approvedPath"], data)
