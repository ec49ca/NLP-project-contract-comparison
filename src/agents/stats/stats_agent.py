"""
Stats Agent - Statistical Analysis and Data Processing

This agent provides statistical analysis and data processing capabilities.
Additional tools to be implemented based on requirements.

## Core Tools to Implement:

1. **Data Analysis**
   - analyze_data
   - generate_statistics
   - create_visualizations

2. **Statistical Operations**
   - calculate_correlation
   - perform_hypothesis_test
   - generate_reports

How tools work:
1. Discovery: client hits /agents/discover to get a list of agents with basic info and tools available
        - agentdiscoveryrequest with filters. each agent returns tools via .get_tools()
2. Tool discovery:
"""

import logging
from typing import Dict, List, Any, Optional
from ...interfaces.agent import AgentInterface
from .tools.descriptive_statistics_tool import DescriptiveStatisticsTool
from .tools.correlation_tool import CorrelationAnalysisTool
from .tools.distribution_analysis_tool import DistributionAnalysisTool
from .tools.outlier_detection_tool import OutlierDetectionTool
from .tools.linear_regression_tool import LinearRegressionTool
from .tools.logistic_regression_tool import LogisticRegressionTool
from .tools.polynomial_regression_tool import PolynomialRegressionTool
from .tools.ridge_regression_tool import RidgeRegressionTool
from .tools.lasso_regression_tool import LassoRegressionTool
from .tools.elastic_net_regression_tool import ElasticNetRegressionTool
from .tools.multiple_regression_tool import MultipleRegressionTool
from .tools.hypothesis_testing_tool import HypothesisTestingTool
from .tools.time_series_regression_tool import TimeSeriesRegressionTool
from uuid import UUID
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class StatsAgent(AgentInterface):
    """Statistics agent for data analysis and statistical operations"""

    def __init__(self):
        self._agent_id_str = "stats"
        self._uuid = None
        self.agent_id = "stats"
        self._name = "Stats Agent"
        self._description = """ Stats Agent is a tool that can be used to analyze data and perform statistical operations.
		It can do the following:
		- Descriptive Statistics
		- Correlation Analysis
		- Distribution Analysis
		- Outlier Detection
		- Linear Regression
		- Logistic Regression
		- Polynomial Regression
		- Ridge Regression
		- Lasso Regression
		- Elastic Net Regression
		- Multiple Regression
		- Time Series Regression
		- Hypothesis Testing"""
        self._initialized = False
        self.category = "data_analysis"
        self.status = "initialized"
        self._tools = {}

        # Add descriptive statistics tool
        self._tools["descriptive_statistics"] = DescriptiveStatisticsTool()

        # Add correlation analysis tool
        self._tools["correlation_analysis"] = CorrelationAnalysisTool()

        # Add distribution analysis tool
        self._tools["distribution_analysis"] = DistributionAnalysisTool()

        # Add outlier detection tool
        self._tools["outlier_detection"] = OutlierDetectionTool()

        # Add individual regression tools
        self._tools["linear_regression"] = LinearRegressionTool()
        self._tools["logistic_regression"] = LogisticRegressionTool()
        self._tools["polynomial_regression"] = PolynomialRegressionTool()
        self._tools["ridge_regression"] = RidgeRegressionTool()
        self._tools["lasso_regression"] = LassoRegressionTool()
        self._tools["elastic_net_regression"] = ElasticNetRegressionTool()
        self._tools["multiple_regression"] = MultipleRegressionTool()
        self._tools["time_series_regression"] = TimeSeriesRegressionTool()
        self._tools["hypothesis_testing"] = HypothesisTestingTool()

    @property
    def agent_id_str(self) -> str:
        """Stable string identifier for the agent type."""
        return self._agent_id_str

    @property
    def uuid(self) -> UUID:
        """The unique, immutable UUID for this agent instance."""
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID):
        """Set the UUID for this agent instance (should only be set once)."""
        if self._uuid is not None:
            raise ValueError("UUID can only be set once")
        self._uuid = value

    @property
    def name(self) -> str:
        """Agent's unique identifier."""
        return self._name

    @property
    def description(self) -> str:
        """Brief description of the agent's purpose."""
        return self._description

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        try:
            logger.info(f"Initializing {self.name} with config: {config}")
            self._initialized = True
            self.status = "ready"
            logger.info(f"{self.name} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {str(e)}")
            self.status = "error"
            raise

    async def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        try:
            logger.info(f"Shutting down {self.name}")
            self._initialized = False
            self.status = "shutdown"
            logger.info(f"{self.name} shutdown successfully")
        except Exception as e:
            logger.error(f"Error during {self.name} shutdown: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "initialized": self._initialized,
            "category": self.category,
            "tools_count": len(self._tools),
            "available_tools": list(self._tools.keys()),
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Return agent's capabilities as a list of objects, each with 'name', 'description', and 'parameters' fields.
        """
        return [
            {
                "name": "descriptive_statistics",
                "description": "Calculate comprehensive descriptive statistics including central tendency (mean, median, mode), dispersion (standard deviation, variance, range, IQR), distribution shape (skewness, kurtosis), and quartiles. Analyzes numeric fields from tabular data to provide statistical insights for data exploration and analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetFields": {
                            "type": "array",
                            "description": "List of field names to analyze (optional - uses all fields if not specified)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["data"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Statistical results for each field including count, mean, median, mode, std_dev, variance, min, max, range, skewness, kurtosis, quartiles, and IQR",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "correlation_analysis",
                "description": "Analyze correlations and relationships between variables using Pearson, Spearman, and Kendall correlation coefficients. Provides comprehensive correlation matrices, significance testing, strong correlation detection, and summary statistics for relationship discovery and predictive modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetFields": {
                            "type": "array",
                            "description": "List of field names to analyze (optional - uses all numeric fields if not specified)",
                            "items": {"type": "string"},
                        },
                        "methods": {
                            "type": "array",
                            "description": "Correlation methods to use: pearson, spearman, kendall (optional - uses all methods if not specified)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["data"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Correlation results including correlations matrix, significance matrix, strong correlations list, and summary statistics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "distribution_analysis",
                "description": "Analyze and test data distributions including normality tests (Shapiro-Wilk, Anderson-Darling, Kolmogorov-Smirnov), distribution fitting (normal, exponential, uniform, lognormal, gamma), goodness-of-fit tests, and comprehensive statistical properties for statistical modeling and validation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetFields": {
                            "type": "array",
                            "description": "List of field names to analyze (optional - uses all numeric fields if not specified)",
                            "items": {"type": "string"},
                        },
                        "tests": {
                            "type": "array",
                            "description": "Analysis types to perform: normality, goodness_of_fit, distribution_fitting (optional - uses all tests if not specified)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["data"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Distribution analysis results including normality tests, distribution fitting, goodness-of-fit tests, descriptive statistics, and histogram data",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "outlier_detection",
                "description": "Identify and analyze statistical outliers in datasets using IQR, Z-score, modified Z-score, and isolation forest methods. Provides comprehensive outlier detection with severity classification, global outlier identification, and method comparison for data quality assessment and anomaly detection.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetFields": {
                            "type": "array",
                            "description": "List of field names to analyze (optional - uses all numeric fields if not specified)",
                            "items": {"type": "string"},
                        },
                        "methods": {
                            "type": "array",
                            "description": "Outlier detection methods to use: iqr, zscore, modified_zscore, isolation_forest (optional - uses all methods if not specified)",
                            "items": {"type": "string"},
                        },
                        "thresholds": {
                            "type": "object",
                            "description": "Custom thresholds for outlier detection methods (optional)",
                            "properties": {
                                "iqr_multiplier": {
                                    "type": "number",
                                    "description": "IQR multiplier threshold (default: 1.5)",
                                },
                                "zscore_threshold": {
                                    "type": "number",
                                    "description": "Z-score threshold (default: 3.0)",
                                },
                                "modified_zscore_threshold": {
                                    "type": "number",
                                    "description": "Modified Z-score threshold (default: 3.5)",
                                },
                                "isolation_forest_contamination": {
                                    "type": "number",
                                    "description": "Isolation forest contamination rate (default: 0.1)",
                                },
                            },
                        },
                    },
                    "required": ["data"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Outlier detection results including outliers by method, global outliers, severity classification, and summary statistics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "linear_regression",
                "description": "Perform basic linear regression analysis with model training, evaluation, and coefficient analysis. Provides R-squared, MSE metrics, residual analysis, and feature importance for linear relationship modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the dependent variable to predict (required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Linear regression results including coefficients, intercept, R-squared, MSE, predictions, residuals, and feature importance",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "logistic_regression",
                "description": "Perform logistic regression for binary classification with accuracy, precision, recall, and F1-score metrics. Includes probability predictions, class distribution analysis, and feature importance for binary outcome modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the binary dependent variable to predict (0 or 1 values required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Logistic regression results including coefficients, intercept, accuracy, precision, recall, F1-score, predictions, probabilities, and feature importance",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "polynomial_regression",
                "description": "Perform polynomial regression for non-linear relationships with configurable degree (1-5). Includes polynomial feature generation, interaction terms for degree 2, complexity metrics, and feature importance for non-linear modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the dependent variable to predict (required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "degree": {
                            "type": "integer",
                            "description": "Polynomial degree (1-5, default: 2)",
                            "minimum": 1,
                            "maximum": 5,
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Polynomial regression results including coefficients, intercept, R-squared, MSE, predictions, residuals, feature importance, and complexity metrics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "ridge_regression",
                "description": "Perform Ridge regression with L2 regularization for handling multicollinearity. Includes feature standardization, coefficient shrinkage analysis, regularization metrics, and feature importance for regularized linear modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the dependent variable to predict (required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "alpha": {
                            "type": "number",
                            "description": "Regularization strength (default: 1.0, must be non-negative)",
                            "minimum": 0,
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Ridge regression results including coefficients, intercept, R-squared, MSE, predictions, residuals, feature importance, and regularization metrics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "lasso_regression",
                "description": "Perform Lasso regression with L1 regularization for automatic feature selection. Includes feature standardization, sparsity analysis, selected features identification, and feature importance for sparse linear modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the dependent variable to predict (required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "alpha": {
                            "type": "number",
                            "description": "Regularization strength (default: 1.0, must be non-negative)",
                            "minimum": 0,
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Lasso regression results including coefficients, intercept, R-squared, MSE, predictions, residuals, feature importance, selected features, and regularization metrics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "elastic_net_regression",
                "description": "Perform Elastic Net regression combining L1 and L2 regularization for feature selection and coefficient shrinkage. Includes configurable alpha and l1_ratio parameters, comprehensive regularization metrics, and feature importance for combined regularization modeling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the dependent variable to predict (required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "alpha": {
                            "type": "number",
                            "description": "Regularization strength (default: 1.0, must be non-negative)",
                            "minimum": 0,
                        },
                        "l1_ratio": {
                            "type": "number",
                            "description": "L1 ratio (0.0-1.0, default: 0.5). 0.0=Ridge, 1.0=Lasso",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Elastic Net regression results including coefficients, intercept, R-squared, MSE, predictions, residuals, feature importance, selected features, and regularization metrics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "multiple_regression",
                "description": "Perform multiple regression with statistical significance testing, F-statistics, p-values, and model diagnostics. Includes interaction terms, adjusted R-squared calculation, coefficient significance analysis, and comprehensive statistical validation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of dictionaries representing rows of a dataset",
                            "items": {"type": "object"},
                        },
                        "targetField": {
                            "type": "string",
                            "description": "Name of the dependent variable to predict (required)",
                        },
                        "featureFields": {
                            "type": "array",
                            "description": "List of independent variable names to use for prediction (default: auto-detect numeric features)",
                            "items": {"type": "string"},
                        },
                        "includeInteractions": {
                            "type": "boolean",
                            "description": "Include interaction terms between features (default: false)",
                        },
                        "testSize": {
                            "type": "number",
                            "description": "Proportion of data for testing (0.0-1.0, default: 0.2)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["data", "targetField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Multiple regression results including coefficients, intercept, R-squared, adjusted R-squared, MSE, predictions, residuals, feature importance, diagnostics, and interaction analysis",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "time_series_regression",
                "description": "Time series forecasting with ARIMA/SARIMA and Exponential Smoothing, STL decomposition, and diagnostics (AIC/BIC, RMSE/MAE, Ljung-Box). Inputs: provide ISO dates (YYYY-MM-01) in the time field and set an explicit frequency (e.g., 'MS' for monthly-start). Seasonal models (SARIMA/seasonal ES) require at least 2 full seasonal cycles at the chosen period (e.g., >=24 months for period=12).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "List of records with a time field (ISO date strings like 'YYYY-MM-01') and a numeric value field. Dates must align to the specified frequency to avoid NaNs.",
                            "items": {"type": "object"},
                        },
                        "timeField": {
                            "type": "string",
                            "description": "Name of the time/date field in the data (default: 'date')",
                        },
                        "valueField": {
                            "type": "string",
                            "description": "Name of the value field to forecast (default: 'value')",
                        },
                        "method": {
                            "type": "string",
                            "description": "Time series method to use: auto_arima, arima, sarima, exponential_smoothing (default: 'auto_arima')",
                        },
                        "frequency": {
                            "type": "string",
                            "description": "Series frequency: D (daily), W (weekly), M (month-end), MS (monthly-start), etc. Recommended: 'MS' for monthly data formatted as YYYY-MM-01. Must match input granularity.",
                        },
                        "confidenceLevel": {
                            "type": "number",
                            "description": "Confidence level for forecast intervals (0-1, default: 0.95)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "testHorizon": {
                            "type": "integer",
                            "description": "Optional out-of-sample holdout size (last N points) for reporting test RMSE/MAE",
                            "minimum": 1,
                        },
                        "order": {
                            "type": "array",
                            "description": "ARIMA order (p, d, q) for manual ARIMA/SARIMA (default: [1, 1, 1])",
                            "items": {"type": "number"},
                        },
                        "seasonalOrder": {
                            "type": "array",
                            "description": "Seasonal order (P, D, Q, s) for SARIMA (default: [1, 1, 1, 12])",
                            "items": {"type": "number"},
                        },
                        "trend": {
                            "type": "string",
                            "description": "Trend component for exponential smoothing: add, mul, None (default: 'add')",
                        },
                        "seasonal": {
                            "type": "string",
                            "description": "Seasonal component for exponential smoothing: add, mul, None (default: 'add'). Omit or set to None for trend-only models.",
                        },
                        "seasonalPeriods": {
                            "type": "number",
                            "description": "Seasonal period (e.g., 12 for monthly). Seasonal models require >=2 full cycles at this period (e.g., >=24 months for 12).",
                        },
                    },
                    "required": ["data", "timeField", "valueField"],
                },
                "returnValues": {
                    "status": "string - Success or error status",
                    "result": "object - Time series regression results including model parameters, forecasts, stationarity tests, decomposition, and performance metrics",
                    "matched_kwargs": "object - The input parameters used for the calculation",
                    "summary": "string - Summary message describing the analysis performed",
                },
            },
            {
                "name": "hypothesis_testing",
                "description": "Hypothesis Testing Suite: t-tests (1-sample, 2-sample independent/paired), ANOVA (one-way), chi-square (independence), and non-parametric tests (Mann-Whitney U, Wilcoxon signed-rank, Kruskal-Wallis). Returns statistic, p-value, effect sizes where applicable, assumptions checks, and reject_null decision at alpha.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "testType": {
                            "type": "string",
                            "description": "one of: t_test_1samp, t_test_2samp_ind, t_test_2samp_paired, anova_oneway, chi_square, mann_whitney_u, wilcoxon_signed_rank, kruskal_wallis",
                        },
                        "sample1": {
                            "type": "array",
                            "description": "numeric array for 1/2-sample tests",
                            "items": {"type": "number"},
                        },
                        "sample2": {
                            "type": "array",
                            "description": "numeric array for 2-sample tests",
                            "items": {"type": "number"},
                        },
                        "samples": {
                            "type": "array",
                            "description": "array of numeric arrays for ANOVA/Kruskal",
                            "items": {"type": "array"},
                        },
                        "contingencyTable": {
                            "type": "array",
                            "description": "2D array for chi-square test of independence",
                            "items": {"type": "array"},
                        },
                        "populationMean": {
                            "type": "number",
                            "description": "population mean for one-sample t-test",
                        },
                        "alternative": {
                            "type": "string",
                            "description": "two-sided | less | greater (where supported)",
                        },
                        "equalVar": {
                            "type": "boolean",
                            "description": "assume equal variances in independent t-test (default: true)",
                        },
                        "alpha": {
                            "type": "number",
                            "description": "significance level (default: 0.05)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["testType"],
                },
                "returnValues": {
                    "status": "string",
                    "result": "object - statistic, p_value, dof (where applicable), effect_size (where applicable), assumptions, reject_null",
                    "matched_kwargs": "object",
                    "summary": "string",
                },
            },
        ]

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request for the Stats Agent"""
        try:
            tool_name = request.get("command")

            if not tool_name:
                return {"status": "error", "message": "Tool name is required"}

            # Execute the appropriate tool
            if tool_name == "descriptive_statistics":
                return await self._tools["descriptive_statistics"].execute_tool(request)
            elif tool_name == "correlation_analysis":
                return await self._tools["correlation_analysis"].execute_tool(request)
            elif tool_name == "distribution_analysis":
                return await self._tools["distribution_analysis"].execute_tool(request)
            elif tool_name == "outlier_detection":
                return await self._tools["outlier_detection"].execute_tool(request)
            elif tool_name == "linear_regression":
                return await self._tools["linear_regression"].execute_tool(request)
            elif tool_name == "logistic_regression":
                return await self._tools["logistic_regression"].execute_tool(request)
            elif tool_name == "polynomial_regression":
                return await self._tools["polynomial_regression"].execute_tool(request)
            elif tool_name == "ridge_regression":
                return await self._tools["ridge_regression"].execute_tool(request)
            elif tool_name == "lasso_regression":
                return await self._tools["lasso_regression"].execute_tool(request)
            elif tool_name == "elastic_net_regression":
                return await self._tools["elastic_net_regression"].execute_tool(request)
            elif tool_name == "multiple_regression":
                return await self._tools["multiple_regression"].execute_tool(request)
            elif tool_name == "time_series_regression":
                return await self._tools["time_series_regression"].execute_tool(request)
            elif tool_name == "hypothesis_testing":
                return await self._tools["hypothesis_testing"].execute_tool(request)
            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error processing request in StatsAgent: {e}")
            return {"status": "error", "message": str(e)}

    # TODO: Add tool-specific processing methods here
    # Example:
    # async def _analyze_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
    #     """Process analyze_data tool requests."""
    #     try:
    #         data = request.get("data")
    #         if not data:
    #             raise ValueError("Data is required for analysis")
    #
    #         # Implement analysis logic here
    #
    #         return {
    #             "status": "success",
    #             "result": "Analysis completed",
    #             "data": data
    #         }
    #     except Exception as e:
    #         logger.error(f"Error in analyze_data: {str(e)}")
    #         return {
    #             "status": "error",
    #             "message": str(e)
    #         }
