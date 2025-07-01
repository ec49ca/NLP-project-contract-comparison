import os
from .pending import PendingToolGraphStorage
from .approved import ApprovedToolGraphStorage
from .rejected import RejectedToolGraphStorage

# Define storage configuration dictionary
storage_config = {
    "pendingPath": os.path.join(os.getcwd(), "pending_tool_graphs.json"),
    "approvedPath": os.path.join(os.getcwd(), "approved_tool_graphs.json"),
    "rejectedPath": os.path.join(os.getcwd(), "rejected_tool_graphs.json"),
}

# Create storage instances
pending_tool_graph_storage = PendingToolGraphStorage(storage_config)
approved_tool_graph_storage = ApprovedToolGraphStorage(storage_config)
rejected_tool_graph_storage = RejectedToolGraphStorage(storage_config)

# Utility functions for the vetting system
def approve_tool_graph(id: str) -> None:
    pending_response = pending_tool_graph_storage.get_tool_graph(id)
    if not pending_response["success"] or not pending_response.get("data"):
        raise Exception(pending_response.get("error", "Failed to get pending tool graph"))

    approved_response = approved_tool_graph_storage.save_tool_graph(id, pending_response["data"])
    if not approved_response["success"]:
        raise Exception(approved_response.get("error", "Failed to save approved tool graph"))

    remove_response = pending_tool_graph_storage.remove_tool_graph(id)
    if not remove_response["success"]:
        raise Exception(remove_response.get("error", "Failed to remove pending tool graph"))

def reject_tool_graph(id: str) -> None:
    pending_response = pending_tool_graph_storage.get_tool_graph(id)
    if not pending_response["success"] or not pending_response.get("data"):
        raise Exception(pending_response.get("error", "Failed to get pending tool graph"))

    rejected_response = rejected_tool_graph_storage.save_tool_graph(id, pending_response["data"])
    if not rejected_response["success"]:
        raise Exception(rejected_response.get("error", "Failed to save rejected tool graph"))

    remove_response = pending_tool_graph_storage.remove_tool_graph(id)
    if not remove_response["success"]:
        raise Exception(remove_response.get("error", "Failed to remove pending tool graph"))
