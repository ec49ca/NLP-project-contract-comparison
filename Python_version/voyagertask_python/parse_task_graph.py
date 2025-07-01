import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FeedbackEntry:
    feedback: str
    taskOutputExample: Optional[str]
    timestamp: str


@dataclass
class VoyagerTask:
    id: str
    query: str
    depends_on: List[str]
    input: Dict[str, str]
    output: Optional[str]
    code: Optional[str] = None
    kwargs: Optional[Dict[str, Any]] = None
    executedoutput: Optional[Any] = None
    kwargs_ex: Optional[Any] = None  # Can be dict, str, or None
    feedbackHistory: Optional[List[FeedbackEntry]] = None
    perceived_query: Optional[str] = None


def parse_task_graph(raw_text: str) -> List[VoyagerTask]:
    tasks: List[VoyagerTask] = []
    current: Dict[str, Any] = {}
    output_variables = set()

    for line in raw_text.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue

        if re.match(r"^\d+\.\s*\(task\d+\)", trimmed):
            if current:
                tasks.append(VoyagerTask(**current))
            task_id_match = re.search(r"\(task\d+\)", trimmed)
            task_query = re.sub(r"^\d+\.\s*\(task\d+\)\s*", "", trimmed).strip()
            current = {
                "id": task_id_match.group(0).replace("(", "").replace(")", "") if task_id_match else "",
                "query": task_query,
                "depends_on": [],
                "input": {},
                "output": None
            }

        elif trimmed.startswith("# depends_on:") and current:
            dep_line = trimmed.replace("# depends_on:", "").strip()
            current["depends_on"] = [dep.strip() for dep in dep_line.split(",") if dep.strip()]

        elif trimmed.startswith("# output:") and current:
            output_var = trimmed.replace("# output:", "").strip()
            current["output"] = output_var
            output_variables.add(output_var)

        elif trimmed.startswith("# input:") and current:
            input_line = trimmed.replace("# input:", "").strip()
            key_value_pairs = [
                pair.split("=") for pair in input_line.split(",")
                if "=" in pair
            ]
            inputs = {k.strip(): v.strip() for k, v in key_value_pairs}

            # Validate inputs exist in output set
            for key, value in inputs.items():
                if value not in output_variables:
                    print(f"⚠️ Warning: Input variable '{value}' in task {current.get('id')} was not declared as an output in any previous task")
            current["input"].update(inputs)

    if current:
        tasks.append(VoyagerTask(**current))

    return tasks
