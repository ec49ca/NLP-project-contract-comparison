from typing import Optional, Any, Dict, List, Union
from dataclasses import dataclass
from enum import Enum

# ---------- Storage Types ----------
class AgentStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class StorageResponse:
    success: bool
    error: Optional[str] = None
    data: Optional[Any] = None

AgentStorage = Dict[str, Any]  # Simplified for Python

@dataclass
class StorageConfig:
    pending_path: str
    approved_path: str
    rejected_path: str

# ---------- Tool Graph Types ----------
@dataclass
class FeedbackEntry:
    feedback: str
    task_output_example: Optional[str] = None
    timestamp: str = ""

@dataclass
class ToolGraphTask:
    id: str
    query: str
    code: str
    input: Dict[str, Any]
    output: Optional[str] = None
    feedback_history: Optional[List['FeedbackEntry']] = None

@dataclass
class ToolGraphData:
    id: str
    query: str
    agent_context: str
    essence_data_hash: str
    task_graph: List['ToolGraphTask']
    created_at: str
    status: AgentStatus
    type: str = "task_graph"

ToolGraphStorage = List[ToolGraphData] 