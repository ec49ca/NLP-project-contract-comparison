"""
Multiple Regression Tool

This tool provides multiple regression capabilities with statistical testing including:
- Multiple linear regression with interaction terms
- Statistical significance testing (F-statistics, p-values)
- Coefficient significance analysis
- Adjusted R-squared calculation
- Model diagnostics and validation
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
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

class MultipleRegressionTool:
    """Tool for multiple regression with statistical testing and diagnostics"""
    
    def __init__(self):
        self.name = "multiple_regression"
        self.description = "Perform multiple regression with statistical significance testing, F-statistics, p-values, and model diagnostics. Includes interaction terms and adjusted R-squared calculation."
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the multiple regression tool"""
        try:
            data = arguments.get("data", [])
            target_field = arguments.get("targetField", "")
            feature_fields = arguments.get("featureFields", [])
            test_size = arguments.get("testSize", 0.2)
            include_interactions = arguments.get("includeInteractions", False)

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": 0
                    },
                    "summary": "No data provided or data format invalid."
                }

            if not target_field:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": "Target field is required for multiple regression analysis."
                }

            # Validate and prepare data
            try:
                valid_data, numerical_features, categorical_features = self._prepare_data(data, target_field, feature_fields)
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": f"Data preparation error: {str(e)}"
                }
            
            if len(valid_data) < 2:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": "Insufficient valid data points for multiple regression analysis."
                }

            # Prepare target and features
            try:
                y = [float(row[target_field]) for row in valid_data]
                X, feature_names = self._create_feature_matrix(valid_data, numerical_features, categorical_features)
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": f"Feature preparation error: {str(e)}"
                }

            # Split data
            try:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": f"Data splitting error: {str(e)}"
                }

            # Run multiple regression
            try:
                result = self._multiple_regression(X_train, X_test, y_train, y_test, feature_names, include_interactions)
                
                return {
                    "status": "success",
                    "result": result,
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": f"Multiple regression analysis completed successfully."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "includeInteractions": include_interactions,
                        "sample_size": len(data)
                    },
                    "summary": f"Multiple regression error: {str(e)}"
                }

        except Exception as e:
            logger.error(f"Error in multiple_regression: {e}")
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": {
                    "targetField": target_field if 'target_field' in locals() else "",
                    "featureFields": feature_fields if 'feature_fields' in locals() else [],
                    "testSize": test_size if 'test_size' in locals() else 0.2,
                    "includeInteractions": include_interactions if 'include_interactions' in locals() else False,
                    "sample_size": len(data) if 'data' in locals() else 0
                }
            }

    def _prepare_data(self, data: List[Dict], target_field: str, feature_fields: List[str]) -> Tuple[List[Dict], List[str], List[str]]:
        """Prepare and validate data for regression"""
        # Filter valid data
        valid_data = []
        for row in data:
            if (target_field in row and 
                isinstance(row[target_field], (int, float)) and 
                not np.isnan(float(row[target_field]))):
                
                # Check if all features exist
                if all(field in row and row[field] is not None and row[field] != '' for field in feature_fields):
                    valid_data.append(row)

        if len(valid_data) < 2:
            raise ValueError("Insufficient valid data points for regression analysis")

        # Separate numerical and categorical features
        numerical_features = []
        categorical_features = []
        
        for feature in feature_fields:
            is_numerical = all(not np.isnan(float(row[feature])) for row in valid_data if isinstance(row[feature], (int, float)))
            if is_numerical:
                numerical_features.append(feature)
            else:
                categorical_features.append(feature)

        return valid_data, numerical_features, categorical_features

    def _create_feature_matrix(self, data: List[Dict], numerical_features: List[str], categorical_features: List[str]) -> Tuple[np.ndarray, List[str]]:
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

    def _multiple_regression(self, X_train: np.ndarray, X_test: np.ndarray, 
                           y_train: List[float], y_test: List[float], 
                           feature_names: List[str], include_interactions: bool = False) -> Dict:
        """Implement multiple regression with interaction terms and statistical testing"""
        try:
            # Create feature matrix with interactions if requested
            if include_interactions and len(feature_names) > 1:
                # Generate interaction terms
                interaction_features = []
                interaction_names = []
                
                for i in range(len(feature_names)):
                    for j in range(i + 1, len(feature_names)):
                        interaction_features.append(X_train[:, i] * X_train[:, j])
                        interaction_names.append(f"{feature_names[i]} * {feature_names[j]}")
                
                # Add interaction terms to feature matrix
                X_train_with_interactions = np.column_stack([X_train] + interaction_features)
                X_test_with_interactions = np.column_stack([X_test] + [X_test[:, i] * X_test[:, j] 
                                                                      for i in range(len(feature_names)) 
                                                                      for j in range(i + 1, len(feature_names))])
                
                final_feature_names = feature_names + interaction_names
                X_train_final = X_train_with_interactions
                X_test_final = X_test_with_interactions
            else:
                final_feature_names = feature_names
                X_train_final = X_train
                X_test_final = X_test
            
            # Fit multiple regression model
            model = LinearRegression()
            model.fit(X_train_final, y_train)
            
            # Make predictions
            y_pred_train = model.predict(X_train_final)
            y_pred_test = model.predict(X_test_final)
            
            # Calculate basic metrics
            r2_train = r2_score(y_train, y_pred_train)
            r2_test = r2_score(y_test, y_pred_test)
            mse_train = mean_squared_error(y_train, y_pred_train)
            mse_test = mean_squared_error(y_test, y_pred_test)
            
            # Calculate adjusted R-squared
            n = len(y_train)
            p = len(final_feature_names)
            adjusted_r2_train = 1 - (1 - r2_train) * (n - 1) / (n - p - 1)
            adjusted_r2_test = 1 - (1 - r2_test) * (len(y_test) - 1) / (len(y_test) - p - 1)
            
            # Calculate residuals
            residuals_train = [float(actual - pred) for actual, pred in zip(y_train, y_pred_train)]
            residuals_test = [float(actual - pred) for actual, pred in zip(y_test, y_pred_test)]
            
            # Statistical significance testing
            # Calculate F-statistic and p-value for overall model
            ss_total = np.sum((np.array(y_train) - np.mean(y_train))**2)
            ss_residual = np.sum((np.array(y_train) - y_pred_train)**2)
            ss_model = ss_total - ss_residual
            
            df_model = p
            df_residual = n - p - 1
            
            if df_residual > 0 and ss_residual > 0:
                f_statistic = (ss_model / df_model) / (ss_residual / df_residual)
                f_p_value = 1 - stats.f.cdf(f_statistic, df_model, df_residual)
            else:
                f_statistic = 0
                f_p_value = 1.0
            
            # Calculate individual coefficient significance
            # Standard errors for coefficients
            mse = ss_residual / df_residual if df_residual > 0 else 0
            
            # Calculate X'X inverse for standard errors
            X_with_intercept = np.column_stack([np.ones(n), X_train_final])
            try:
                XtX_inv = np.linalg.inv(X_with_intercept.T @ X_with_intercept)
                standard_errors = np.sqrt(np.diag(XtX_inv) * mse)
                t_statistics = model.coef_ / standard_errors[1:]  # Skip intercept
                p_values = 2 * (1 - stats.t.cdf(np.abs(t_statistics), df_residual))
            except np.linalg.LinAlgError:
                # Handle singular matrix case
                standard_errors = np.full(len(model.coef_), np.nan)
                t_statistics = np.full(len(model.coef_), np.nan)
                p_values = np.full(len(model.coef_), np.nan)
            
            # Feature importance (coefficients)
            feature_importance = dict(zip(final_feature_names, model.coef_.tolist()))
            
            # Model diagnostics
            diagnostics = {
                "f_statistic": float(f_statistic),
                "f_p_value": float(f_p_value),
                "degrees_of_freedom_model": df_model,
                "degrees_of_freedom_residual": df_residual,
                "standard_errors": standard_errors[1:].tolist(),  # Skip intercept
                "t_statistics": t_statistics.tolist(),
                "p_values": p_values.tolist(),
                "significant_features": [final_feature_names[i] for i in range(len(final_feature_names)) 
                                      if p_values[i] < 0.05],
                "highly_significant_features": [final_feature_names[i] for i in range(len(final_feature_names)) 
                                             if p_values[i] < 0.01]
            }
            
            # Interaction analysis
            interaction_analysis = {}
            if include_interactions:
                interaction_terms = [name for name in final_feature_names if " * " in name]
                interaction_analysis = {
                    "interaction_terms": interaction_terms,
                    "interaction_coefficients": {name: model.coef_[final_feature_names.index(name)] 
                                              for name in interaction_terms},
                    "significant_interactions": [name for name in interaction_terms 
                                             if p_values[final_feature_names.index(name)] < 0.05]
                }
            
            return {
                "status": "success",
                "method": "multiple_regression",
                "coefficients": model.coef_.tolist(),
                "intercept": float(model.intercept_),
                "r_squared_train": float(r2_train),
                "r_squared_test": float(r2_test),
                "adjusted_r_squared_train": float(adjusted_r2_train),
                "adjusted_r_squared_test": float(adjusted_r2_test),
                "mse_train": float(mse_train),
                "mse_test": float(mse_test),
                "predictions_train": y_pred_train.tolist(),
                "predictions_test": y_pred_test.tolist(),
                "residuals_train": residuals_train,
                "residuals_test": residuals_test,
                "feature_importance": feature_importance,
                "feature_names": final_feature_names,
                "diagnostics": diagnostics,
                "interaction_analysis": interaction_analysis,
                "include_interactions": include_interactions,
                "summary": f"Multiple regression completed with {len(final_feature_names)} features. R² = {r2_test:.4f}, Adjusted R² = {adjusted_r2_test:.4f}, F-statistic = {f_statistic:.4f} (p = {f_p_value:.4f})"
            }
            
        except Exception as e:
            logger.error(f"Error in multiple regression: {e}")
            return {
                "status": "error",
                "method": "multiple_regression",
                "message": str(e)
            }