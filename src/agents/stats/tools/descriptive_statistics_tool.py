"""
Descriptive Statistics Tool

This tool calculates descriptive statistics from data.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np
from scipy import stats
from collections import Counter
from ....services.llm_service import llm_service
from ....services.prompt_service import prompt_service

logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


class DescriptiveStatisticsTool:
    """Tool for calculating descriptive statistics from data"""

    def __init__(self):
        self.name = "descriptive_statistics"
        self.description = "Calculate descriptive statistics from data"
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the descriptive statistics tool"""
        try:
            data = arguments.get("data", [])
            target_fields = arguments.get("targetFields", [])

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": arguments,
                    "summary": "No data provided or data format invalid.",
                }

            # If no target fields specified, use all fields from first row
            if not target_fields and data:
                target_fields = list(data[0].keys())

            result = {}

            for field in target_fields:
                # Extract valid numeric values (excluding booleans which are technically int subclass)
                values = [
                    row[field]
                    for row in data
                    if field in row
                    and isinstance(row[field], (int, float))
                    and not isinstance(row[field], bool)
                ]

                if not values:
                    continue

                sorted_values = sorted(values)
                q1 = np.percentile(sorted_values, 25)
                q2 = np.percentile(sorted_values, 50)
                q3 = np.percentile(sorted_values, 75)
                iqr = q3 - q1
                mean = np.mean(values)
                std_dev = np.std(values, ddof=1)  # Sample standard deviation
                variance = np.var(values, ddof=1)  # Sample variance
                min_val = np.min(values)
                max_val = np.max(values)
                mode = self._calc_mode(values)
                skewness = stats.skew(values)  # Use scipy for accurate skewness
                kurtosis = stats.kurtosis(values)  # Use scipy for accurate kurtosis

                result[field] = {
                    "count": len(values),
                    "mean": mean,
                    "median": q2,
                    "mode": mode,
                    "std_dev": std_dev,
                    "variance": variance,
                    "min": min_val,
                    "max": max_val,
                    "range": max_val - min_val,
                    "skewness": skewness,
                    "kurtosis": kurtosis,
                    "quartiles": {"q1": q1, "q2": q2, "q3": q3},
                    "iqr": iqr,
                }

            # Convert numpy types to Python native types for JSON serialization
            result = convert_numpy_types(result)

            return {
                "status": "success",
                "result": result,
                "matched_kwargs": arguments,
                "summary": f"Descriptive stats computed for {len(result)} field(s).",
            }

        except Exception as e:
            logger.error(f"Error in descriptive_statistics: {e}")
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": arguments,
            }

    def _calc_mode(self, values: List[float]) -> Any:
        """Calculate mode of a list of values"""
        counter = Counter(values)
        most_common = counter.most_common()
        if not most_common:
            return None
        max_freq = most_common[0][1]
        modes = [val for val, freq in most_common if freq == max_freq]
        return modes[0] if len(modes) == 1 else modes


