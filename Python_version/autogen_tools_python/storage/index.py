import os
from pathlib import Path
from typing import Any, Dict

from .pending import PendingStorage
from .approved import ApprovedStorage
from .rejected import RejectedStorage
from .base import StorageResponse


# ---------- Storage Paths ----------
storage_config = {
    "pendingPath": str(Path(os.getcwd()) / "pending_agents.json"),
    "approvedPath": str(Path(os.getcwd()) / "dynamic_agents.json"),
    "rejectedPath": str(Path(os.getcwd()) / "rejected_agents.json"),
}

# ---------- Storage Instances ----------
pending_storage = PendingStorage(storage_config)
approved_storage = ApprovedStorage(storage_config)
rejected_storage = RejectedStorage(storage_config)


# ---------- Main Save/Retrieve ----------
def save_agent(agent_name: str, agent_data: Any) -> None:
    response: StorageResponse = pending_storage.save_agent(agent_name, agent_data)
    if not response["success"]:
        raise RuntimeError(response.get("error", "Failed to save agent"))


def retrieve_agents() -> Dict[str, Any]:
    response: StorageResponse = approved_storage.get_all_agents()
    if not response["success"] or response.get("data") is None:
        raise RuntimeError(response.get("error", "Failed to retrieve agents"))
    return response["data"]


# ---------- Vetting System ----------
async def approve_agent(agent_name: str) -> None:
    pending_response = pending_storage.get_agent(agent_name)
    if not pending_response["success"] or pending_response.get("data") is None:
        raise RuntimeError(pending_response.get("error", "Failed to get pending agent"))

    approved_response = approved_storage.save_agent(agent_name, pending_response["data"])
    if not approved_response["success"]:
        raise RuntimeError(approved_response.get("error", "Failed to save approved agent"))

    remove_response = pending_storage.remove_agent(agent_name)
    if not remove_response["success"]:
        raise RuntimeError(remove_response.get("error", "Failed to remove pending agent"))


async def reject_agent(agent_name: str) -> None:
    pending_response = pending_storage.get_agent(agent_name)
    if not pending_response["success"] or pending_response.get("data") is None:
        raise RuntimeError(pending_response.get("error", "Failed to get pending agent"))

    rejected_response = rejected_storage.save_agent(agent_name, pending_response["data"])
    if not rejected_response["success"]:
        raise RuntimeError(rejected_response.get("error", "Failed to save rejected agent"))

    remove_response = pending_storage.remove_agent(agent_name)
    if not remove_response["success"]:
        raise RuntimeError(remove_response.get("error", "Failed to remove pending agent"))


async def get_pending_agents() -> Dict[str, Any]:
    response = pending_storage.get_all_agents()
    if not response["success"] or response.get("data") is None:
        raise RuntimeError(response.get("error", "Failed to get pending agents"))
    return response["data"]
