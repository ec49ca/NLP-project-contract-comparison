import json
import os

def load_combined_essence_context(files: list[str]) -> list[dict]:
    combined = []
    for file in files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    combined.extend(data)
                else:
                    print(f"⚠️ File {file} did not contain a list of objects")
        except Exception as e:
            print(f"❌ Error loading file {file}: {e}")
    return combined
