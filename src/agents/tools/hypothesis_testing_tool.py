import numpy as np
from typing import Any, Dict, List, Optional
from scipy import stats


class HypothesisTestingTool:
    """
    Hypothesis Testing Suite.

    Supported tests:
    - t-tests: one-sample, independent two-sample, paired two-sample
    - ANOVA: one-way
    - Chi-square tests: contingency table (independence)
    - Non-parametric: Mann-Whitney U, Wilcoxon signed-rank, Kruskal-Wallis

    Inputs (depending on testType):
    - testType: one of [
        "t_test_1samp", "t_test_2samp_ind", "t_test_2samp_paired",
        "anova_oneway", "chi_square",
        "mann_whitney_u", "wilcoxon_signed_rank", "kruskal_wallis"
      ]
    - sample1: array of numbers (for 1-sample and 2-sample tests)
    - sample2: array of numbers (for 2-sample tests)
    - samples: array of arrays (for ANOVA/Kruskal)
    - contingencyTable: array of arrays (for chi-square)
    - populationMean: number (for one-sample t-test)
    - alternative: "two-sided" | "less" | "greater" (where supported)
    - equalVar: boolean (for independent t-test; default True)
    - alpha: number (0-1) for significance reporting (default 0.05)

    Outputs:
    - statistic, p_value, degrees_of_freedom (when applicable)
    - effect_size (Cohen's d for t-tests where applicable)
    - assumptions (normality via Shapiro, variance via Levene where applicable)
    - decision (reject_null at alpha)
    """

    def __init__(self) -> None:
        self.name = "hypothesis_testing"
        self.description = (
            "Perform hypothesis tests: t-tests (1-sample, 2-sample), ANOVA, chi-square, "
            "and non-parametric tests (Mann-Whitney U, Wilcoxon, Kruskal-Wallis)."
        )

    def convert_numpy_types(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: self.convert_numpy_types(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.convert_numpy_types(v) for v in obj]
        return obj

    def _shapiro_safe(self, x: np.ndarray) -> Optional[Dict[str, float]]:
        try:
            if len(x) >= 3:
                w, p = stats.shapiro(x)
                return {"statistic": float(w), "p_value": float(p)}
        except Exception:
            pass
        return None

    def _levene_safe(self, x: np.ndarray, y: np.ndarray) -> Optional[Dict[str, float]]:
        try:
            if len(x) >= 2 and len(y) >= 2:
                w, p = stats.levene(x, y)
                return {"statistic": float(w), "p_value": float(p)}
        except Exception:
            pass
        return None

    def _cohens_d_independent(self, x: np.ndarray, y: np.ndarray) -> Optional[float]:
        try:
            nx, ny = len(x), len(y)
            if nx < 2 or ny < 2:
                return None
            sx2, sy2 = np.var(x, ddof=1), np.var(y, ddof=1)
            s_pooled = np.sqrt(((nx - 1) * sx2 + (ny - 1) * sy2) / (nx + ny - 2))
            if s_pooled == 0:
                return None
            return float((np.mean(x) - np.mean(y)) / s_pooled)
        except Exception:
            return None

    def _cohens_d_one_sample(self, x: np.ndarray, mu: float) -> Optional[float]:
        try:
            sx = np.std(x, ddof=1)
            if sx == 0:
                return None
            return float((np.mean(x) - mu) / sx)
        except Exception:
            return None

    async def execute_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            test_type = request.get("testType")
            alpha = float(request.get("alpha", 0.05))
            alternative = request.get("alternative", "two-sided")
            equal_var = bool(request.get("equalVar", True))

            if not test_type:
                return {
                    "status": "error",
                    "result": "Parameter 'testType' is required",
                    "matched_kwargs": request,
                    "summary": "Missing required parameter: testType"
                }

            result: Dict[str, Any] = {"test": test_type}

            if test_type == "t_test_1samp":
                sample1 = np.asarray(request.get("sample1", []), dtype=float)
                mu = request.get("populationMean")
                if mu is None or len(sample1) < 2:
                    return {"status": "error", "result": "populationMean and at least 2 values required", "matched_kwargs": request, "summary": "Invalid input for one-sample t-test"}
                t_stat, p_val = stats.ttest_1samp(sample1, popmean=float(mu), alternative=alternative)
                df = len(sample1) - 1
                result.update({
                    "statistic": float(t_stat),
                    "p_value": float(p_val),
                    "degrees_of_freedom": int(df),
                    "effect_size": self._cohens_d_one_sample(sample1, float(mu)),
                    "assumptions": {
                        "normality_sample1": self._shapiro_safe(sample1)
                    }
                })

            elif test_type == "t_test_2samp_ind":
                x = np.asarray(request.get("sample1", []), dtype=float)
                y = np.asarray(request.get("sample2", []), dtype=float)
                if len(x) < 2 or len(y) < 2:
                    return {"status": "error", "result": "sample1 and sample2 require at least 2 values each", "matched_kwargs": request, "summary": "Invalid input for independent t-test"}
                t_stat, p_val = stats.ttest_ind(x, y, equal_var=equal_var, alternative=alternative)
                df = (len(x) + len(y) - 2) if equal_var else None
                result.update({
                    "statistic": float(t_stat),
                    "p_value": float(p_val),
                    "degrees_of_freedom": int(df) if df is not None else None,
                    "effect_size": self._cohens_d_independent(x, y),
                    "assumptions": {
                        "normality_sample1": self._shapiro_safe(x),
                        "normality_sample2": self._shapiro_safe(y),
                        "variance_equality": self._levene_safe(x, y) if equal_var else None
                    }
                })

            elif test_type == "t_test_2samp_paired":
                x = np.asarray(request.get("sample1", []), dtype=float)
                y = np.asarray(request.get("sample2", []), dtype=float)
                if len(x) < 2 or len(y) < 2 or len(x) != len(y):
                    return {"status": "error", "result": "sample1 and sample2 must be same length (>=2)", "matched_kwargs": request, "summary": "Invalid input for paired t-test"}
                t_stat, p_val = stats.ttest_rel(x, y, alternative=alternative)
                df = len(x) - 1
                diff = x - y
                result.update({
                    "statistic": float(t_stat),
                    "p_value": float(p_val),
                    "degrees_of_freedom": int(df),
                    "effect_size": self._cohens_d_one_sample(diff, 0.0),
                    "assumptions": {
                        "normality_of_differences": self._shapiro_safe(diff)
                    }
                })

            elif test_type == "anova_oneway":
                samples = request.get("samples", [])
                if not samples or not all(len(s) >= 2 for s in samples):
                    return {"status": "error", "result": "Provide 'samples' as list of arrays, each with >=2 values", "matched_kwargs": request, "summary": "Invalid input for ANOVA"}
                arrays = [np.asarray(s, dtype=float) for s in samples]
                f_stat, p_val = stats.f_oneway(*arrays)
                result.update({
                    "statistic": float(f_stat),
                    "p_value": float(p_val),
                    "groups": len(arrays),
                    "assumptions": {
                        "normality_each_group": [self._shapiro_safe(a) for a in arrays],
                        "variance_equality": (lambda res: {"statistic": float(res.statistic), "p_value": float(res.pvalue)}) (stats.levene(*arrays)) if all(len(a) >= 2 for a in arrays) else None
                    }
                })

            elif test_type == "chi_square":
                table = np.asarray(request.get("contingencyTable", []), dtype=float)
                if table.ndim != 2 or table.shape[0] < 2 or table.shape[1] < 2:
                    return {"status": "error", "result": "contingencyTable must be 2D with at least 2x2", "matched_kwargs": request, "summary": "Invalid input for Chi-square"}
                chi2, p_val, dof, expected = stats.chi2_contingency(table, correction=False)
                result.update({
                    "statistic": float(chi2),
                    "p_value": float(p_val),
                    "degrees_of_freedom": int(dof),
                    "expected": expected.tolist()
                })

            elif test_type == "mann_whitney_u":
                x = np.asarray(request.get("sample1", []), dtype=float)
                y = np.asarray(request.get("sample2", []), dtype=float)
                if len(x) < 1 or len(y) < 1:
                    return {"status": "error", "result": "sample1 and sample2 require at least 1 value", "matched_kwargs": request, "summary": "Invalid input for Mann-Whitney U"}
                u_stat, p_val = stats.mannwhitneyu(x, y, alternative=alternative)
                result.update({
                    "statistic": float(u_stat),
                    "p_value": float(p_val)
                })

            elif test_type == "wilcoxon_signed_rank":
                x = np.asarray(request.get("sample1", []), dtype=float)
                y = np.asarray(request.get("sample2", []), dtype=float)
                if len(x) < 1 or len(y) < 1 or len(x) != len(y):
                    return {"status": "error", "result": "sample1 and sample2 must be same length (>=1)", "matched_kwargs": request, "summary": "Invalid input for Wilcoxon"}
                w_stat, p_val = stats.wilcoxon(x, y, alternative=alternative, zero_method="wilcox")
                result.update({
                    "statistic": float(w_stat),
                    "p_value": float(p_val)
                })

            elif test_type == "kruskal_wallis":
                samples = request.get("samples", [])
                if not samples or not all(len(s) >= 1 for s in samples):
                    return {"status": "error", "result": "Provide 'samples' as list of arrays, each with >=1 value", "matched_kwargs": request, "summary": "Invalid input for Kruskal-Wallis"}
                arrays = [np.asarray(s, dtype=float) for s in samples]
                h_stat, p_val = stats.kruskal(*arrays)
                result.update({
                    "statistic": float(h_stat),
                    "p_value": float(p_val),
                    "groups": len(arrays)
                })

            else:
                return {"status": "error", "result": f"Unknown testType: {test_type}", "matched_kwargs": request, "summary": f"Unknown testType: {test_type}"}

            # Decision
            reject = (result.get("p_value") is not None) and (result["p_value"] < alpha)
            result["alpha"] = alpha
            result["reject_null"] = bool(reject)

            return {
                "status": "success",
                "result": self.convert_numpy_types(result),
                "matched_kwargs": request,
                "summary": f"{test_type} completed. statistic={result.get('statistic')}, p={result.get('p_value')}, reject_null={result.get('reject_null')}"
            }

        except Exception as e:
            return {
                "status": "error",
                "result": f"Hypothesis testing failed: {e}",
                "matched_kwargs": request,
                "summary": f"Hypothesis testing failed: {e}"
            }
