"""
Elastic Net Regression Tool

This tool provides Elastic Net regression capabilities combining L1 and L2 regularization including:
- Combined L1 and L2 regularization
- Configurable alpha (regularization strength) and l1_ratio (L1/L2 balance)
- Feature standardization
- Feature selection with coefficient shrinkage
- Comprehensive regularization metrics
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
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


class ElasticNetRegressionTool:
    """Tool for Elastic Net regression combining L1 and L2 regularization"""

    def __init__(self):
        self.name = "elastic_net_regression"
        self.description = "Perform Elastic Net regression combining L1 and L2 regularization for feature selection and coefficient shrinkage. Includes configurable alpha and l1_ratio parameters."
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the Elastic Net regression tool"""
        try:
            data = arguments.get("data", [])
            target_field = arguments.get("targetField", "")
            feature_fields = arguments.get("featureFields", [])
            test_size = arguments.get("testSize", 0.2)
            alpha = arguments.get("alpha", 1.0)
            l1_ratio = arguments.get("l1_ratio", 0.5)

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": 0,
                    },
                    "summary": "No data provided or data format invalid.",
                }

            if not target_field:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": "Target field is required for Elastic Net regression analysis.",
                }

            # Validate and prepare data
            try:
                valid_data, numerical_features, categorical_features = (
                    self._prepare_data(data, target_field, feature_fields)
                )
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": f"Data preparation error: {str(e)}",
                }

            if len(valid_data) < 2:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": "Insufficient valid data points for Elastic Net regression analysis.",
                }

            # Prepare target and features
            try:
                y = [float(row[target_field]) for row in valid_data]
                X, feature_names = self._create_feature_matrix(
                    valid_data, numerical_features, categorical_features
                )
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": f"Feature preparation error: {str(e)}",
                }

            # Split data
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=42
                )
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": f"Data splitting error: {str(e)}",
                }

            # Run Elastic Net regression
            try:
                hyperparameters = {"alpha": alpha, "l1_ratio": l1_ratio}
                result = self._elastic_net_regression(
                    X_train, X_test, y_train, y_test, feature_names, hyperparameters
                )

                return {
                    "status": "success",
                    "result": result,
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": f"Elastic Net regression analysis completed successfully.",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "alpha": alpha,
                        "l1_ratio": l1_ratio,
                        "sample_size": len(data),
                    },
                    "summary": f"Elastic Net regression error: {str(e)}",
                }

        except Exception as e:
            logger.error("Error in elastic_net_regression", extra={'error': str(e)})
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": {
                    "targetField": target_field if "target_field" in locals() else "",
                    "featureFields": (
                        feature_fields if "feature_fields" in locals() else []
                    ),
                    "testSize": test_size if "test_size" in locals() else 0.2,
                    "alpha": alpha if "alpha" in locals() else 1.0,
                    "l1_ratio": l1_ratio if "l1_ratio" in locals() else 0.5,
                    "sample_size": len(data) if "data" in locals() else 0,
                },
            }

    def _prepare_data(
        self, data: List[Dict], target_field: str, feature_fields: List[str]
    ) -> Tuple[List[Dict], List[str], List[str]]:
        """Prepare and validate data for regression"""
        # Filter valid data
        valid_data = []
        for row in data:
            if (
                target_field in row
                and isinstance(row[target_field], (int, float))
                and not np.isnan(float(row[target_field]))
            ):

                # Check if all features exist
                if all(
                    field in row and row[field] is not None and row[field] != ""
                    for field in feature_fields
                ):
                    valid_data.append(row)

        if len(valid_data) < 2:
            raise ValueError("Insufficient valid data points for regression analysis")

        # Separate numerical and categorical features
        numerical_features = []
        categorical_features = []

        for feature in feature_fields:
            is_numerical = all(
                not np.isnan(float(row[feature]))
                for row in valid_data
                if isinstance(row[feature], (int, float))
            )
            if is_numerical:
                numerical_features.append(feature)
            else:
                categorical_features.append(feature)

        return valid_data, numerical_features, categorical_features

    def _create_feature_matrix(
        self,
        data: List[Dict],
        numerical_features: List[str],
        categorical_features: List[str],
    ) -> Tuple[np.ndarray, List[str]]:
        """Create feature matrix with encoded categorical variables"""
        feature_names = numerical_features.copy()

        # Create one-hot encoding for categorical features
        categorical_encodings = {}
        for feature in categorical_features:
            unique_values = list(set(str(row[feature]) for row in data))
            categorical_encodings[feature] = unique_values
            # Add encoded feature names (excluding first category)
            for value in unique_values[1:]:
                feature_names.append(f"{feature}_{value}")

        # Create feature matrix
        X = []
        for row in data:
            features = []

            # Add numerical features
            for feature in numerical_features:
                features.append(float(row[feature]))

            # Add encoded categorical features
            for feature in categorical_features:
                value = str(row[feature])
                unique_values = categorical_encodings[feature]
                # One-hot encoding (excluding first category)
                for unique_value in unique_values[1:]:
                    features.append(1.0 if value == unique_value else 0.0)

            X.append(features)

        return np.array(X), feature_names

    def _elastic_net_regression(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_train: List[float],
        y_test: List[float],
        feature_names: List[str],
        hyperparameters: Dict,
    ) -> Dict:
        """Implement elastic net regression combining L1 and L2 regularization"""
        try:
            # Get alpha (regularization strength) and l1_ratio from hyperparameters
            alpha = hyperparameters.get("alpha", 1.0)
            l1_ratio = hyperparameters.get("l1_ratio", 0.5)

            # Validate parameters
            if alpha < 0:
                return {
                    "status": "error",
                    "method": "elastic_net",
                    "message": f"Invalid alpha: {alpha}. Must be non-negative.",
                }

            if l1_ratio < 0 or l1_ratio > 1:
                return {
                    "status": "error",
                    "method": "elastic_net",
                    "message": f"Invalid l1_ratio: {l1_ratio}. Must be between 0 and 1.",
                }

            # Standardize features for Elastic Net regression
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Fit Elastic Net regression model
            model = ElasticNet(
                alpha=alpha, l1_ratio=l1_ratio, random_state=42, max_iter=1000
            )
            model.fit(X_train_scaled, y_train)

            # Make predictions
            y_pred_train = model.predict(X_train_scaled)
            y_pred_test = model.predict(X_test_scaled)

            # Calculate metrics
            r2_train = r2_score(y_train, y_pred_train)
            r2_test = r2_score(y_test, y_pred_test)
            mse_train = mean_squared_error(y_train, y_pred_train)
            mse_test = mean_squared_error(y_test, y_pred_test)

            # Calculate residuals
            residuals_train = [
                float(actual - pred) for actual, pred in zip(y_train, y_pred_train)
            ]
            residuals_test = [
                float(actual - pred) for actual, pred in zip(y_test, y_pred_test)
            ]

            # Transform coefficients back to original scale
            original_coefficients = model.coef_ / scaler.scale_
            original_intercept = model.intercept_ - np.sum(
                original_coefficients * scaler.mean_
            )

            # Identify selected features (non-zero coefficients)
            selected_features = [
                feature_names[i]
                for i in range(len(feature_names))
                if abs(original_coefficients[i]) > 1e-6
            ]

            # Feature importance (coefficients in original scale)
            feature_importance = dict(
                zip(feature_names, original_coefficients.tolist())
            )

            # Calculate regularization and feature selection metrics
            l1_penalty = float(np.sum(np.abs(model.coef_)))
            l2_penalty = float(np.sum(model.coef_**2))
            total_penalty = l1_penalty + l2_penalty

            regularization_metrics = {
                "alpha": alpha,
                "l1_ratio": l1_ratio,
                "l1_penalty": l1_penalty,
                "l2_penalty": l2_penalty,
                "total_penalty": total_penalty,
                "coefficient_shrinkage": float(np.mean(np.abs(model.coef_))),
                "sparsity_ratio": float(np.sum(model.coef_ == 0) / len(model.coef_)),
                "selected_features_count": len(selected_features),
                "total_features_count": len(feature_names),
                "regularization_type": f"Elastic Net (L1: {l1_ratio:.2f}, L2: {1-l1_ratio:.2f})",
            }

            return {
                "status": "success",
                "method": "elastic_net",
                "alpha": alpha,
                "l1_ratio": l1_ratio,
                "coefficients": original_coefficients.tolist(),
                "intercept": float(original_intercept),
                "r_squared_train": float(r2_train),
                "r_squared_test": float(r2_test),
                "mse_train": float(mse_train),
                "mse_test": float(mse_test),
                "predictions_train": y_pred_train.tolist(),
                "predictions_test": y_pred_test.tolist(),
                "residuals_train": residuals_train,
                "residuals_test": residuals_test,
                "feature_importance": feature_importance,
                "feature_names": feature_names,
                "selected_features": selected_features,
                "regularization_metrics": regularization_metrics,
                "summary": f"Elastic Net regression (α={alpha}, l1_ratio={l1_ratio}) completed with {len(selected_features)}/{len(feature_names)} features selected. R² = {r2_test:.4f}, MSE = {mse_test:.4f}",
            }

        except Exception as e:
            logger.error("Error in elastic net regression", extra={'error': str(e)})
            return {"status": "error", "method": "elastic_net", "message": str(e)}
