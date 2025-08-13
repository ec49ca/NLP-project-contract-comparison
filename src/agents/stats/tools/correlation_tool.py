"""
Correlation Analysis Tool

This tool analyzes correlations and relationships between variables using Pearson, Spearman,
and Kendall correlation coefficients for relationship discovery and predictive modeling.
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


class CorrelationAnalysisTool:
    """Tool for analyzing correlations between variables"""

    def __init__(self):
        self.name = "correlation_analysis"
        self.description = "Analyze correlations and relationships between variables using Pearson, Spearman, and Kendall correlation coefficients"
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the correlation analysis tool"""
        try:
            data = arguments.get("data", [])
            target_fields = arguments.get("targetFields", [])
            methods = arguments.get("methods", ["pearson", "spearman", "kendall"])

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": arguments,
                    "summary": "No data provided or data format invalid.",
                }

            # If no target fields specified, use all numeric fields from first row
            if not target_fields and data:
                target_fields = self._get_numeric_fields(data[0])

            if len(target_fields) < 2:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": arguments,
                    "summary": "Need at least 2 numeric fields for correlation analysis.",
                }

            result = {
                "correlations": {},
                "significance_matrix": {},
                "strong_correlations": [],
                "summary_stats": {},
            }

            # Calculate correlations for each method
            for method in methods:
                if method not in ["pearson", "spearman", "kendall"]:
                    continue

                method_correlations = {}
                method_significance = {}

                for i, field1 in enumerate(target_fields):
                    method_correlations[field1] = {}
                    method_significance[field1] = {}

                    for j, field2 in enumerate(target_fields):
                        if i == j:
                            # Diagonal: perfect correlation with self
                            method_correlations[field1][field2] = {
                                "correlation": 1.0,
                                "p_value": 0.0,
                                "significance": "high",
                                "interpretation": "Perfect correlation (same variable)",
                            }
                            method_significance[field1][field2] = 1.0
                        else:
                            # Calculate correlation between different fields
                            correlation_result = self._calculate_correlation(
                                data, field1, field2, method
                            )

                            if correlation_result:
                                method_correlations[field1][field2] = correlation_result
                                method_significance[field1][field2] = (
                                    correlation_result["p_value"]
                                )
                            else:
                                method_correlations[field1][field2] = {
                                    "correlation": 0.0,
                                    "p_value": 1.0,
                                    "significance": "none",
                                    "interpretation": "Insufficient data for correlation",
                                }
                                method_significance[field1][field2] = 1.0

                result["correlations"][method] = method_correlations
                result["significance_matrix"][method] = method_significance

            # Find strong correlations across all methods
            result["strong_correlations"] = self._find_strong_correlations(
                result["correlations"], target_fields
            )

            # Calculate summary statistics
            result["summary_stats"] = self._calculate_correlation_summary(
                result["correlations"], target_fields
            )

            # Convert numpy types to Python native types for JSON serialization
            result = convert_numpy_types(result)

            return {
                "status": "success",
                "result": result,
                "matched_kwargs": {
                    "targetFields": target_fields,
                    "methods": methods,
                    "sample_size": len(data),
                },
                "summary": f"Correlation analysis completed for {len(target_fields)} fields using {len(methods)} methods.",
            }

        except Exception as e:
            logger.error(f"Error in correlation_analysis: {e}")
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": {
                    "targetFields": (
                        target_fields if "target_fields" in locals() else []
                    ),
                    "methods": methods if "methods" in locals() else [],
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

    def _calculate_correlation(
        self, data: List[Dict[str, Any]], field1: str, field2: str, method: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate correlation between two fields using specified method"""
        try:
            # Extract valid numeric pairs
            pairs = []
            for row in data:
                val1 = row.get(field1)
                val2 = row.get(field2)

                if (
                    isinstance(val1, (int, float))
                    and isinstance(val2, (int, float))
                    and not isinstance(val1, bool)
                    and not isinstance(val2, bool)
                    and not np.isnan(val1)
                    and not np.isnan(val2)
                ):
                    pairs.append((val1, val2))

            if len(pairs) < 3:
                return None

            values1 = [pair[0] for pair in pairs]
            values2 = [pair[1] for pair in pairs]

            # Calculate correlation based on method
            if method == "pearson":
                correlation, p_value = stats.pearsonr(values1, values2)
            elif method == "spearman":
                correlation, p_value = stats.spearmanr(values1, values2)
            elif method == "kendall":
                correlation, p_value = stats.kendalltau(values1, values2)
            else:
                return None

            # Determine significance level
            significance = self._determine_significance(p_value)

            # Generate interpretation
            interpretation = self._interpret_correlation(
                correlation, significance, field1, field2
            )

            return {
                "correlation": float(correlation),
                "p_value": float(p_value),
                "significance": significance,
                "interpretation": interpretation,
                "sample_size": len(pairs),
            }

        except Exception as e:
            logger.error(
                f"Error calculating {method} correlation between {field1} and {field2}: {e}"
            )
            return None

    def _determine_significance(self, p_value: float) -> str:
        """Determine significance level based on p-value"""
        if p_value < 0.001:
            return "extreme"
        elif p_value < 0.01:
            return "high"
        elif p_value < 0.05:
            return "medium"
        elif p_value < 0.1:
            return "low"
        else:
            return "none"

    def _interpret_correlation(
        self, correlation: float, significance: str, field1: str, field2: str
    ) -> str:
        """Generate human-readable interpretation of correlation"""
        abs_corr = abs(correlation)

        if abs_corr < 0.1:
            strength = "negligible"
        elif abs_corr < 0.3:
            strength = "weak"
        elif abs_corr < 0.5:
            strength = "moderate"
        elif abs_corr < 0.7:
            strength = "strong"
        elif abs_corr < 0.9:
            strength = "very strong"
        else:
            strength = "near perfect"

        direction = "positive" if correlation > 0 else "negative"

        if significance == "none":
            return f"No significant correlation between {field1} and {field2}"
        else:
            return f"{strength.capitalize()} {direction} correlation between {field1} and {field2} (r = {correlation:.3f})"

    def _find_strong_correlations(
        self, correlations: Dict[str, Any], fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Find correlations with absolute value > 0.5 across all methods"""
        strong_correlations = []

        for method, method_corrs in correlations.items():
            for field1 in fields:
                for field2 in fields:
                    if field1 != field2:
                        corr_data = method_corrs.get(field1, {}).get(field2, {})
                        if corr_data and abs(corr_data.get("correlation", 0)) > 0.5:
                            strong_correlations.append(
                                {
                                    "method": method,
                                    "field1": field1,
                                    "field2": field2,
                                    "correlation": corr_data["correlation"],
                                    "p_value": corr_data["p_value"],
                                    "significance": corr_data["significance"],
                                    "interpretation": corr_data["interpretation"],
                                }
                            )

        # Sort by absolute correlation value
        strong_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return strong_correlations

    def _calculate_correlation_summary(
        self, correlations: Dict[str, Any], fields: List[str]
    ) -> Dict[str, Any]:
        """Calculate summary statistics for correlation analysis"""
        summary = {
            "total_variable_pairs": len(fields) * (len(fields) - 1) // 2,
            "methods_used": list(correlations.keys()),
            "correlation_ranges": {},
            "significance_counts": {},
        }

        for method in correlations.keys():
            method_corrs = correlations[method]
            correlations_list = []
            significance_counts = {
                "extreme": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "none": 0,
            }

            for field1 in fields:
                for field2 in fields:
                    if field1 != field2:
                        corr_data = method_corrs.get(field1, {}).get(field2, {})
                        if corr_data:
                            correlations_list.append(corr_data["correlation"])
                            significance_counts[corr_data["significance"]] += 1

            if correlations_list:
                summary["correlation_ranges"][method] = {
                    "min": min(correlations_list),
                    "max": max(correlations_list),
                    "mean": np.mean(correlations_list),
                    "std": np.std(correlations_list),
                }
                summary["significance_counts"][method] = significance_counts

        return convert_numpy_types(summary)
