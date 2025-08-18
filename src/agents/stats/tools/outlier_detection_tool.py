"""
Outlier Detection System

This tool identifies and analyzes statistical outliers in datasets using IQR, Z-score,
and other methods for data quality assessment and anomaly detection.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats
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


class OutlierDetectionTool:
    """Tool for detecting outliers in datasets"""

    def __init__(self):
        self.name = "outlier_detection"
        self.description = "Identify and analyze statistical outliers in datasets using IQR, Z-score, and other methods"
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the outlier detection tool"""
        try:
            data = arguments.get("data", [])
            target_fields = arguments.get("targetFields", [])
            methods = arguments.get(
                "methods", ["iqr", "zscore", "modified_zscore", "isolation_forest"]
            )
            thresholds = arguments.get(
                "thresholds",
                {
                    "iqr_multiplier": 1.5,
                    "zscore_threshold": 3.0,
                    "modified_zscore_threshold": 3.5,
                    "isolation_forest_contamination": 0.1,
                },
            )

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetFields": target_fields,
                        "methods": methods,
                        "thresholds": thresholds,
                        "sample_size": 0,
                    },
                    "summary": "No data provided or data format invalid.",
                }

            # If no target fields specified, use all numeric fields from first row
            if not target_fields and data:
                target_fields = self._get_numeric_fields(data[0])

            if not target_fields:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetFields": target_fields,
                        "methods": methods,
                        "thresholds": thresholds,
                        "sample_size": len(data),
                    },
                    "summary": "No numeric fields found for outlier detection.",
                }

            result = {"outliers": {}, "summary_stats": {}, "global_outliers": []}

            # Analyze each field
            for field in target_fields:
                values_with_indices = self._extract_numeric_values_with_indices(
                    data, field
                )

                if len(values_with_indices) < 10:
                    logger.warning(
                        "Insufficient data for field",
                        extra={
                            'field': field,
                            'num_values': len(values_with_indices),
                        },
                    )
                    continue

                field_analysis = {
                    "sample_size": len(values_with_indices),
                    "methods": {},
                    "summary": {},
                }

                # Apply each detection method
                for method in methods:
                    if method == "iqr":
                        field_analysis["methods"]["iqr"] = self._detect_outliers_iqr(
                            values_with_indices, thresholds.get("iqr_multiplier", 1.5)
                        )
                    elif method == "zscore":
                        field_analysis["methods"]["zscore"] = (
                            self._detect_outliers_zscore(
                                values_with_indices,
                                thresholds.get("zscore_threshold", 3.0),
                            )
                        )
                    elif method == "modified_zscore":
                        field_analysis["methods"]["modified_zscore"] = (
                            self._detect_outliers_modified_zscore(
                                values_with_indices,
                                thresholds.get("modified_zscore_threshold", 3.5),
                            )
                        )
                    elif method == "isolation_forest":
                        field_analysis["methods"]["isolation_forest"] = (
                            self._detect_outliers_isolation_forest(
                                values_with_indices,
                                thresholds.get("isolation_forest_contamination", 0.1),
                            )
                        )

                # Calculate summary statistics for the field
                field_analysis["summary"] = self._calculate_outlier_summary(
                    field_analysis["methods"]
                )

                result["outliers"][field] = field_analysis

            # Find global outliers (outliers detected by multiple methods)
            result["global_outliers"] = self._find_global_outliers(result["outliers"])

            # Calculate overall summary statistics
            result["summary_stats"] = self._calculate_overall_summary(
                result["outliers"]
            )

            # Convert numpy types to Python native types for JSON serialization
            result = convert_numpy_types(result)

            return {
                "status": "success",
                "result": result,
                "matched_kwargs": {
                    "targetFields": target_fields,
                    "methods": methods,
                    "thresholds": thresholds,
                    "sample_size": len(data),
                },
                "summary": f"Outlier detection completed for {len(result['outliers'])} fields using {len(methods)} methods.",
            }

        except Exception as e:
            logger.error("Error in outlier_detection", extra={'error': str(e)})
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": {
                    "targetFields": (
                        target_fields if "target_fields" in locals() else []
                    ),
                    "methods": methods if "methods" in locals() else [],
                    "thresholds": thresholds if "thresholds" in locals() else {},
                    "sample_size": len(data) if "data" in locals() else 0,
                },
            }

    def _get_numeric_fields(self, row: Dict[str, Any]) -> List[str]:
        """Extract numeric fields from a data row"""
        numeric_fields = []
        for field, value in row.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_fields.append(field)
        return numeric_fields

    def _extract_numeric_values_with_indices(
        self, data: List[Dict[str, Any]], field: str
    ) -> List[Tuple[int, float]]:
        """Extract valid numeric values with their row indices"""
        values_with_indices = []
        for i, row in enumerate(data):
            value = row.get(field)
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and not np.isnan(value)
            ):
                values_with_indices.append((i, float(value)))
        return values_with_indices

    def _detect_outliers_iqr(
        self, values_with_indices: List[Tuple[int, float]], multiplier: float
    ) -> Dict[str, Any]:
        """Detect outliers using IQR method"""
        try:
            values = [val for _, val in values_with_indices]
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1

            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr

            outliers = []
            for idx, value in values_with_indices:
                if value < lower_bound or value > upper_bound:
                    score = abs(value - (q1 + q3) / 2) / iqr
                    outliers.append(
                        {
                            "index": idx,
                            "value": value,
                            "score": float(score),
                            "severity": self._determine_severity(score),
                            "bound": "lower" if value < lower_bound else "upper",
                            "distance_from_bound": float(
                                abs(
                                    value
                                    - (
                                        lower_bound
                                        if value < lower_bound
                                        else upper_bound
                                    )
                                )
                            ),
                        }
                    )

            outliers.sort(key=lambda x: x["score"], reverse=True)

            return {
                "outliers": outliers,
                "total_outliers": len(outliers),
                "outlier_percentage": (len(outliers) / len(values)) * 100,
                "threshold": multiplier,
                "bounds": {"lower": float(lower_bound), "upper": float(upper_bound)},
                "iqr": float(iqr),
                "quartiles": {"q1": float(q1), "q3": float(q3)},
            }
        except Exception as e:
            logger.error("Error in IQR outlier detection", extra={'error': str(e)})
            return {"error": str(e)}

    def _detect_outliers_zscore(
        self, values_with_indices: List[Tuple[int, float]], threshold: float
    ) -> Dict[str, Any]:
        """Detect outliers using Z-score method"""
        try:
            values = [val for _, val in values_with_indices]
            mean = np.mean(values)
            std = np.std(values)

            outliers = []
            for idx, value in values_with_indices:
                z_score = abs((value - mean) / std)
                if z_score > threshold:
                    outliers.append(
                        {
                            "index": idx,
                            "value": value,
                            "score": float(z_score),
                            "severity": self._determine_severity(z_score),
                            "z_score": float((value - mean) / std),
                            "distance_from_mean": float(abs(value - mean)),
                        }
                    )

            outliers.sort(key=lambda x: x["score"], reverse=True)

            return {
                "outliers": outliers,
                "total_outliers": len(outliers),
                "outlier_percentage": (len(outliers) / len(values)) * 100,
                "threshold": threshold,
                "mean": float(mean),
                "std": float(std),
            }
        except Exception as e:
            logger.error("Error in Z-score outlier detection", extra={'error': str(e)})
            return {"error": str(e)}

    def _detect_outliers_modified_zscore(
        self, values_with_indices: List[Tuple[int, float]], threshold: float
    ) -> Dict[str, Any]:
        """Detect outliers using Modified Z-score method"""
        try:
            values = [val for _, val in values_with_indices]
            median = np.median(values)

            # Calculate Median Absolute Deviation (MAD)
            mad = np.median(np.abs(values - median))
            modified_mad = mad * 1.4826  # Constant for normal distribution

            outliers = []
            for idx, value in values_with_indices:
                modified_z_score = abs(0.6745 * (value - median) / modified_mad)
                if modified_z_score > threshold:
                    outliers.append(
                        {
                            "index": idx,
                            "value": value,
                            "score": float(modified_z_score),
                            "severity": self._determine_severity(modified_z_score),
                            "modified_z_score": float(
                                0.6745 * (value - median) / modified_mad
                            ),
                            "distance_from_median": float(abs(value - median)),
                        }
                    )

            outliers.sort(key=lambda x: x["score"], reverse=True)

            return {
                "outliers": outliers,
                "total_outliers": len(outliers),
                "outlier_percentage": (len(outliers) / len(values)) * 100,
                "threshold": threshold,
                "median": float(median),
                "mad": float(mad),
                "modified_mad": float(modified_mad),
            }
        except Exception as e:
            logger.error("Error in Modified Z-score outlier detection", extra={'error': str(e)})
            return {"error": str(e)}

    def _detect_outliers_isolation_forest(
        self, values_with_indices: List[Tuple[int, float]], contamination: float
    ) -> Dict[str, Any]:
        """Detect outliers using simplified Isolation Forest approach"""
        try:
            values = [val for _, val in values_with_indices]
            mean = np.mean(values)
            std = np.std(values)

            # Simplified isolation forest using distance-based approach
            # In practice, you'd use sklearn.ensemble.IsolationForest
            distances = [abs(val - mean) / std for val in values]
            threshold = np.percentile(distances, (1 - contamination) * 100)

            outliers = []
            for i, (idx, value) in enumerate(values_with_indices):
                distance = distances[i]
                if distance > threshold:
                    outliers.append(
                        {
                            "index": idx,
                            "value": value,
                            "score": float(distance),
                            "severity": self._determine_severity(distance),
                            "distance_from_mean": float(abs(value - mean)),
                            "normalized_distance": float(distance),
                        }
                    )

            outliers.sort(key=lambda x: x["score"], reverse=True)

            return {
                "outliers": outliers,
                "total_outliers": len(outliers),
                "outlier_percentage": (len(outliers) / len(values)) * 100,
                "contamination": contamination,
                "threshold": float(threshold),
                "mean": float(mean),
                "std": float(std),
            }
        except Exception as e:
            logger.error("Error in Isolation Forest outlier detection", extra={'error': str(e)})
            return {"error": str(e)}

    def _determine_severity(self, score: float) -> str:
        """Determine severity level based on outlier score"""
        if score > 5:
            return "extreme"
        elif score > 3:
            return "high"
        elif score > 2:
            return "medium"
        else:
            return "low"

    def _calculate_outlier_summary(self, methods: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics for outlier detection methods"""
        try:
            summary = {
                "total_outliers": 0,
                "methods_used": list(methods.keys()),
                "severity_counts": {"extreme": 0, "high": 0, "medium": 0, "low": 0},
                "method_comparison": {},
            }

            for method_name, method_result in methods.items():
                if "error" not in method_result:
                    outliers = method_result.get("outliers", [])
                    summary["total_outliers"] += len(outliers)

                    # Count severities
                    for outlier in outliers:
                        severity = outlier.get("severity", "low")
                        summary["severity_counts"][severity] += 1

                    # Method comparison
                    summary["method_comparison"][method_name] = {
                        "outliers_found": len(outliers),
                        "outlier_percentage": method_result.get(
                            "outlier_percentage", 0
                        ),
                        "threshold": method_result.get("threshold", 0),
                    }

            return summary

        except Exception as e:
            logger.error("Error calculating outlier summary", extra={'error': str(e)})
            return {"error": str(e)}

    def _find_global_outliers(self, outliers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find outliers detected by multiple methods"""
        try:
            global_outliers = {}

            for field, field_analysis in outliers.items():
                for method_name, method_result in field_analysis.get(
                    "methods", {}
                ).items():
                    if "error" not in method_result:
                        for outlier in method_result.get("outliers", []):
                            key = (field, outlier["index"])
                            if key not in global_outliers:
                                global_outliers[key] = {
                                    "field": field,
                                    "index": outlier["index"],
                                    "value": outlier["value"],
                                    "detected_by": [],
                                    "severity": outlier["severity"],
                                }
                            global_outliers[key]["detected_by"].append(method_name)

            # Filter to outliers detected by multiple methods
            multi_method_outliers = [
                outlier
                for outlier in global_outliers.values()
                if len(outlier["detected_by"]) > 1
            ]

            # Sort by number of methods that detected them
            multi_method_outliers.sort(
                key=lambda x: len(x["detected_by"]), reverse=True
            )

            return multi_method_outliers

        except Exception as e:
            logger.error("Error finding global outliers", extra={'error': str(e)})
            return []

    def _calculate_overall_summary(self, outliers: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall summary statistics"""
        try:
            summary = {
                "total_fields": len(outliers),
                "fields_with_outliers": 0,
                "total_outliers": 0,
                "global_outliers": 0,
                "severity_distribution": {
                    "extreme": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                },
                "method_effectiveness": {},
            }

            for field, field_analysis in outliers.items():
                field_summary = field_analysis.get("summary", {})
                if field_summary.get("total_outliers", 0) > 0:
                    summary["fields_with_outliers"] += 1

                summary["total_outliers"] += field_summary.get("total_outliers", 0)

                # Count severities
                for severity, count in field_summary.get("severity_counts", {}).items():
                    summary["severity_distribution"][severity] += count

            return summary

        except Exception as e:
            logger.error("Error calculating overall summary", extra={'error': str(e)})
            return {"error": str(e)}
