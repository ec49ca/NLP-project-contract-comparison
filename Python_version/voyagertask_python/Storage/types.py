from typing import TypedDict, List, Dict, Optional, Any


class VoyagerTask(TypedDict, total=False):
    id: str
    query: str
    depends_on: List[str]
    input: Dict[str, str]
    output: Optional[str]
    code: Optional[str]
    kwargs: Optional[Dict[str, Any]]
    executedoutput: Optional[Any]
    kwargs_ex: Optional[Any]
    feedbackHistory: Optional[List[Dict[str, Any]]]
    perceived_query: Optional[str]


class MergedFunctionMetadata(TypedDict, total=False):
    originalTaskCount: int
    mergedFunctionName: str
    dependenciesResolved: List[str]


class MergedFunctionResult(TypedDict, total=False):
    code: str
    metadata: Optional[MergedFunctionMetadata]
    output: Optional[Any]
    testSuccess: Optional[bool]
    testError: Optional[str]


class StorageResponse(TypedDict, total=False):
    success: bool
    error: Optional[str]
    data: Optional[Any]


class PendingToolGraphEntry(TypedDict, total=False):
    id: str
    query: str
    task_graph: List[VoyagerTask]
    created_at: str
    mergedFunction: Optional[MergedFunctionResult]


ToolGraphStorage = Dict[str, PendingToolGraphEntry]
