import os
import json
import hashlib
import uuid
from typing import Any


BASE_DIR = os.getcwd()

# Paths
TAG_FILE = os.path.join(BASE_DIR, "tag_master.json")
CAPABILITY_FILE = os.path.join(BASE_DIR, "capability_master.json")


# ------------------- Hash Generation --------------------

def generate_hash(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:8]

# Fixed simple generateHash (no crypto.subtle, browser-safe) - matches JS version
def generate_hash_simple(text: str) -> str:
    hash_val = 0
    for char in text:
        hash_val = (hash_val << 5) - hash_val + ord(char)
        hash_val &= 0xFFFFFFFF  # Convert to 32-bit int
    return hex(abs(hash_val))[2:10]


# ------------------- Tag Helpers --------------------

def load_tags() -> list[str]:
    if not os.path.exists(TAG_FILE):
        return []
    with open(TAG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tags(tag_list: list[str]) -> None:
    with open(TAG_FILE, "w", encoding="utf-8") as f:
        json.dump(tag_list, f, indent=2)


# ------------------- Capability Helpers --------------------

def load_capabilities() -> list[str]:
    if not os.path.exists(CAPABILITY_FILE):
        return []
    with open(CAPABILITY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_capabilities(capabilities: list[str]) -> None:
    with open(CAPABILITY_FILE, "w", encoding="utf-8") as f:
        json.dump(capabilities, f, indent=2)


# ------------------- Essence Helpers --------------------

def fetch_essence(essence_files: list[str]) -> list[Any]:
    essence_data = []
    for file in essence_files:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                essence_data.extend(json_data)
    return essence_data

def fetch_essence_json_string(essence_files: list[str]) -> str:
    return json.dumps(fetch_essence(essence_files), indent=2)


# ------------------- Field Map and Schema Helpers --------------------

def describe_field_schema(field_value_map: dict[str, list[Any]]) -> dict[str, dict[str, Any]]:
    if not field_value_map:
        return {}

    summary = {}
    for field, values in field_value_map.items():
        samples = values[:5]
        types = list(set(type(v).__name__ for v in samples))
        summary[field] = {
            "types": types,
            "sample_values": samples
        }
    return summary


def get_field_value_map(data: list[dict[str, Any]]) -> dict[str, list[str]]:
    field_map: dict[str, set[str]] = {}

    if not isinstance(data, list) or not all(isinstance(entry, dict) for entry in data):
        return {}

    for entry in data:
        for key, value in entry.items():
            if isinstance(value, (str, int, float)):
                field_map.setdefault(key, set()).add(str(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (str, int, float)):
                        field_map.setdefault(key, set()).add(str(item))
            elif isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    if isinstance(sub_val, (str, int, float)):
                        combined_key = f"{key}.{sub_key}"
                        field_map.setdefault(combined_key, set()).add(str(sub_val))

    return {k: list(v) for k, v in field_map.items()}


# ------------------- Output Schema Helpers --------------------

def infer_output_schema(output: Any) -> dict[str, Any]:
    if isinstance(output, list):
        if len(output) == 0:
            return {"type": "array", "items": {"type": "unknown"}, "note": "empty output"}
        if all(isinstance(i, (str, int, float)) for i in output):
            return {"type": "array", "items": {"type": type(output[0]).__name__}}
        if all(isinstance(i, list) for i in output):
            return {"type": "array", "items": {"type": "array"}}
        if all(isinstance(i, dict) for i in output):
            return {"type": "array", "items": {"type": "object"}}
    return {"type": type(output).__name__}


# ------------------- Agent Metadata Helpers --------------------

def generate_unique_id(query: str) -> str:
    hash_digest = hashlib.sha256(query.lower().encode()).hexdigest()
    return str(uuid.UUID(bytes=bytes.fromhex(hash_digest[:32])))

def extract_tags_from_kwargs(kwargs: dict[str, Any]) -> list[str]:
    return list(kwargs.keys())

def build_input_schema(kwargs_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            k: {"type": "string"} for k in kwargs_dict.keys()
        },
        "required": list(kwargs_dict.keys())
    }

def build_example_block(kwargs_dict: dict[str, Any], output_example: Any) -> list[dict[str, Any]]:
    return [{
        "input": kwargs_dict,
        "output": output_example or "Example output not captured yet"
    }]
