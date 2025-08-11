"""
Distribution Analysis Tool

This tool analyzes and tests data distributions including normality tests, distribution fitting, 
and goodness-of-fit tests for statistical modeling and validation.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats
from scipy.stats import norm, expon, uniform, lognorm, gamma, beta
from ...services.llm_service import llm_service
from ...services.prompt_service import prompt_service

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


class DistributionAnalysisTool:
    """Tool for analyzing data distributions and performing goodness-of-fit tests"""

    def __init__(self):
        self.name = "distribution_analysis"
        self.description = "Analyze and test data distributions including normality tests, distribution fitting, and goodness-of-fit tests"
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the distribution analysis tool"""
        try:
            data = arguments.get("data", [])
            target_fields = arguments.get("targetFields", [])
            tests = arguments.get("tests", ["normality", "goodness_of_fit", "distribution_fitting"])
            
            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetFields": target_fields,
                        "tests": tests,
                        "sample_size": 0
                    },
                    "summary": "No data provided or data format invalid."
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
                        "tests": tests,
                        "sample_size": len(data)
                    },
                    "summary": "No numeric fields found for distribution analysis."
                }

            result = {
                "distributions": {},
                "summary_stats": {}
            }

            # Analyze each field
            for field in target_fields:
                values = self._extract_numeric_values(data, field)
                
                if len(values) < 10:
                    logger.warning(f"Insufficient data for field {field}: {len(values)} values")
                    continue
                
                field_analysis = {
                    "sample_size": len(values),
                    "normality_test": {},
                    "distribution_fitting": {},
                    "descriptive_stats": {},
                    "histogram_data": {}
                }
                
                # Normality test
                if "normality" in tests:
                    field_analysis["normality_test"] = self._perform_normality_test(values)
                
                # Distribution fitting
                if "distribution_fitting" in tests:
                    field_analysis["distribution_fitting"] = self._fit_distributions(values)
                
                # Goodness of fit tests
                if "goodness_of_fit" in tests:
                    field_analysis["goodness_of_fit"] = self._perform_goodness_of_fit_tests(values)
                
                # Descriptive statistics for distribution analysis
                field_analysis["descriptive_stats"] = self._calculate_distribution_stats(values)
                
                # Histogram data for visualization
                field_analysis["histogram_data"] = self._generate_histogram_data(values)
                
                result["distributions"][field] = field_analysis

            # Calculate summary statistics across all fields
            result["summary_stats"] = self._calculate_summary_stats(result["distributions"])

            # Convert numpy types to Python native types for JSON serialization
            result = convert_numpy_types(result)

            return {
                "status": "success",
                "result": result,
                "matched_kwargs": {
                    "targetFields": target_fields,
                    "tests": tests,
                    "sample_size": len(data)
                },
                "summary": f"Distribution analysis completed for {len(result['distributions'])} fields."
            }

        except Exception as e:
            logger.error(f"Error in distribution_analysis: {e}")
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": {
                    "targetFields": target_fields if 'target_fields' in locals() else [],
                    "tests": tests if 'tests' in locals() else [],
                    "sample_size": len(data) if 'data' in locals() else 0
                }
            }

    def _get_numeric_fields(self, row: Dict[str, Any]) -> List[str]:
        """Extract numeric fields from a data row"""
        numeric_fields = []
        for field, value in row.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_fields.append(field)
        return numeric_fields

    def _extract_numeric_values(self, data: List[Dict[str, Any]], field: str) -> List[float]:
        """Extract valid numeric values for a field"""
        values = []
        for row in data:
            value = row.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and not np.isnan(value):
                values.append(float(value))
        return values

    def _perform_normality_test(self, values: List[float]) -> Dict[str, Any]:
        """Perform normality tests on the data"""
        try:
            # Shapiro-Wilk test
            shapiro_stat, shapiro_p = stats.shapiro(values)
            
            # Anderson-Darling test
            anderson_result = stats.anderson(values)
            
            # Kolmogorov-Smirnov test against normal distribution
            mean = np.mean(values)
            std = np.std(values)
            ks_stat, ks_p = stats.kstest(values, 'norm', args=(mean, std))
            
            # Determine if data is normal based on p-values
            is_normal = shapiro_p > 0.05 and ks_p > 0.05
            
            return {
                "shapiro_wilk": {
                    "statistic": float(shapiro_stat),
                    "p_value": float(shapiro_p),
                    "interpretation": "Normal" if shapiro_p > 0.05 else "Not normal"
                },
                "anderson_darling": {
                    "statistic": float(anderson_result.statistic),
                    "critical_values": anderson_result.critical_values.tolist(),
                    "significance_levels": anderson_result.significance_level.tolist(),
                    "interpretation": "Normal" if anderson_result.statistic < anderson_result.critical_values[2] else "Not normal"
                },
                "kolmogorov_smirnov": {
                    "statistic": float(ks_stat),
                    "p_value": float(ks_p),
                    "interpretation": "Normal" if ks_p > 0.05 else "Not normal"
                },
                "overall_conclusion": "Normal" if is_normal else "Not normal",
                "confidence": "high" if is_normal else "low"
            }
        except Exception as e:
            logger.error(f"Error in normality test: {e}")
            return {"error": str(e)}

    def _fit_distributions(self, values: List[float]) -> Dict[str, Any]:
        """Fit various probability distributions to the data"""
        try:
            distributions = {
                "normal": {"dist": norm, "params": []},
                "exponential": {"dist": expon, "params": []},
                "uniform": {"dist": uniform, "params": []},
                "lognormal": {"dist": lognorm, "params": []},
                "gamma": {"dist": gamma, "params": []}
            }
            
            fits = {}
            
            for name, dist_info in distributions.items():
                try:
                    if name == "normal":
                        params = dist_info["dist"].fit(values)
                        fitted_dist = dist_info["dist"](*params)
                    elif name == "exponential":
                        params = dist_info["dist"].fit(values)
                        fitted_dist = dist_info["dist"](*params)
                    elif name == "uniform":
                        params = dist_info["dist"].fit(values)
                        fitted_dist = dist_info["dist"](*params)
                    elif name == "lognormal":
                        params = dist_info["dist"].fit(values)
                        fitted_dist = dist_info["dist"](*params)
                    elif name == "gamma":
                        params = dist_info["dist"].fit(values)
                        fitted_dist = dist_info["dist"](*params)
                    
                    # Calculate goodness of fit using Kolmogorov-Smirnov test
                    ks_stat, ks_p = stats.kstest(values, fitted_dist.cdf)
                    
                    # Calculate AIC and BIC
                    log_likelihood = np.sum(fitted_dist.logpdf(values))
                    aic = 2 * len(params) - 2 * log_likelihood
                    bic = len(params) * np.log(len(values)) - 2 * log_likelihood
                    
                    fits[name] = {
                        "parameters": params.tolist() if hasattr(params, 'tolist') else list(params),
                        "ks_statistic": float(ks_stat),
                        "ks_p_value": float(ks_p),
                        "aic": float(aic),
                        "bic": float(bic),
                        "log_likelihood": float(log_likelihood)
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not fit {name} distribution: {e}")
                    continue
            
            # Find best fit based on AIC
            if fits:
                best_fit = min(fits.keys(), key=lambda x: fits[x]["aic"])
                fits["best_fit"] = best_fit
                fits["best_fit_details"] = fits[best_fit]
            
            return fits
            
        except Exception as e:
            logger.error(f"Error in distribution fitting: {e}")
            return {"error": str(e)}

    def _perform_goodness_of_fit_tests(self, values: List[float]) -> Dict[str, Any]:
        """Perform goodness of fit tests"""
        try:
            # Chi-square test (using histogram)
            hist, bin_edges = np.histogram(values, bins='auto')
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            
            # Expected frequencies assuming normal distribution
            mean = np.mean(values)
            std = np.std(values)
            expected = norm.pdf(bin_centers, mean, std) * len(values) * (bin_edges[1] - bin_edges[0])
            
            # Remove bins with zero expected frequency
            valid_indices = expected > 0
            observed = hist[valid_indices]
            expected_valid = expected[valid_indices]
            
            if len(observed) > 1:
                chi2_stat, chi2_p = stats.chisquare(observed, expected_valid)
            else:
                chi2_stat, chi2_p = np.nan, np.nan
            
            return {
                "chi_square": {
                    "statistic": float(chi2_stat) if not np.isnan(chi2_stat) else None,
                    "p_value": float(chi2_p) if not np.isnan(chi2_p) else None,
                    "interpretation": "Good fit" if chi2_p > 0.05 else "Poor fit"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in goodness of fit tests: {e}")
            return {"error": str(e)}

    def _calculate_distribution_stats(self, values: List[float]) -> Dict[str, Any]:
        """Calculate descriptive statistics for distribution analysis"""
        try:
            mean = np.mean(values)
            std = np.std(values)
            skewness = stats.skew(values)
            kurtosis = stats.kurtosis(values)
            
            # Percentiles
            percentiles = np.percentile(values, [5, 10, 25, 50, 75, 90, 95])
            
            return {
                "mean": float(mean),
                "std": float(std),
                "skewness": float(skewness),
                "kurtosis": float(kurtosis),
                "percentiles": {
                    "p5": float(percentiles[0]),
                    "p10": float(percentiles[1]),
                    "p25": float(percentiles[2]),
                    "p50": float(percentiles[3]),
                    "p75": float(percentiles[4]),
                    "p90": float(percentiles[5]),
                    "p95": float(percentiles[6])
                },
                "range": float(np.max(values) - np.min(values)),
                "iqr": float(np.percentile(values, 75) - np.percentile(values, 25))
            }
        except Exception as e:
            logger.error(f"Error calculating distribution stats: {e}")
            return {"error": str(e)}

    def _generate_histogram_data(self, values: List[float]) -> Dict[str, Any]:
        """Generate histogram data for visualization"""
        try:
            hist, bin_edges = np.histogram(values, bins='auto')
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            
            return {
                "histogram": hist.tolist(),
                "bin_edges": bin_edges.tolist(),
                "bin_centers": bin_centers.tolist(),
                "density": (hist / len(values)).tolist()
            }
        except Exception as e:
            logger.error(f"Error generating histogram data: {e}")
            return {"error": str(e)}

    def _calculate_summary_stats(self, distributions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics across all fields"""
        try:
            summary = {
                "total_fields": len(distributions),
                "normal_distributions": 0,
                "non_normal_distributions": 0,
                "best_fits": {},
                "overall_conclusions": []
            }
            
            for field, analysis in distributions.items():
                normality = analysis.get("normality_test", {})
                if normality.get("overall_conclusion") == "Normal":
                    summary["normal_distributions"] += 1
                else:
                    summary["non_normal_distributions"] += 1
                
                fitting = analysis.get("distribution_fitting", {})
                if "best_fit" in fitting:
                    best_fit = fitting["best_fit"]
                    summary["best_fits"][field] = best_fit
                
                # Add field-specific conclusions
                field_conclusion = {
                    "field": field,
                    "sample_size": analysis.get("sample_size", 0),
                    "normality": normality.get("overall_conclusion", "Unknown"),
                    "best_fit": fitting.get("best_fit", "Unknown")
                }
                summary["overall_conclusions"].append(field_conclusion)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating summary stats: {e}")
            return {"error": str(e)} 