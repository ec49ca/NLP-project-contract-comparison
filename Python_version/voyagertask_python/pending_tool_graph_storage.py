from datetime import datetime
from typing import Optional, Dict, Any
from voyagertask_python.Storage.types import PendingToolGraphEntry
from voyagertask_python.Storage.index import pending_tool_graph_storage

def save_pending_tool_graph(entry: Dict[str, Any]) -> None:
    entry_with_timestamp: Dict[str, Any] = {
        **entry,
        "created_at": datetime.utcnow().isoformat()
    }
    response = pending_tool_graph_storage.save_tool_graph(entry["id"], entry_with_timestamp)
    if not response["success"]:
        raise Exception(response.get("error", "Failed to save pending tool graph"))

def get_pending_tool_graph(graph_id: str) -> Optional[Dict[str, Any]]:
    response = pending_tool_graph_storage.get_tool_graph(graph_id)
    if not response["success"] or "data" not in response:
        return None
    return response["data"]

def get_all_pending_tool_graphs() -> Dict[str, Any]:
    response = pending_tool_graph_storage.get_all_tool_graphs()
    if not response["success"] or "data" not in response:
        return {}
    return response["data"]

def remove_pending_tool_graph(graph_id: str) -> bool:
    response = pending_tool_graph_storage.remove_tool_graph(graph_id)
    return response["success"]
