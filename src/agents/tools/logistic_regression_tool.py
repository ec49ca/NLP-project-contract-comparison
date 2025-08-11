"""
Logistic Regression Tool

This tool provides logistic regression capabilities for binary classification including:
- Binary classification model training
- Accuracy, precision, recall, F1-score metrics
- Probability predictions
- Class distribution analysis
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
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

class LogisticRegressionTool:
    """Tool for logistic regression binary classification"""
    
    def __init__(self):
        self.name = "logistic_regression"
        self.description = "Perform logistic regression for binary classification with accuracy, precision, recall, and F1-score metrics. Includes probability predictions and class distribution analysis."
        self.llm_service = llm_service

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the logistic regression tool"""
        try:
            data = arguments.get("data", [])
            target_field = arguments.get("targetField", "")
            feature_fields = arguments.get("featureFields", [])
            test_size = arguments.get("testSize", 0.2)

            if not data or not isinstance(data, list):
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
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
                        "sample_size": len(data)
                    },
                    "summary": "Target field is required for logistic regression analysis."
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
                        "sample_size": len(data)
                    },
                    "summary": "Insufficient valid data points for logistic regression analysis."
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
                        "sample_size": len(data)
                    },
                    "summary": f"Data splitting error: {str(e)}"
                }

            # Run logistic regression
            try:
                result = self._logistic_regression(X_train, X_test, y_train, y_test, feature_names)
                
                return {
                    "status": "success",
                    "result": result,
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "sample_size": len(data)
                    },
                    "summary": f"Logistic regression analysis completed successfully."
                }
            except Exception as e:
                return {
                    "status": "error",
                    "result": {},
                    "matched_kwargs": {
                        "targetField": target_field,
                        "featureFields": feature_fields,
                        "testSize": test_size,
                        "sample_size": len(data)
                    },
                    "summary": f"Logistic regression error: {str(e)}"
                }

        except Exception as e:
            logger.error(f"Error in logistic_regression: {e}")
            return {
                "status": "error",
                "message": str(e),
                "result": {},
                "matched_kwargs": {
                    "targetField": target_field if 'target_field' in locals() else "",
                    "featureFields": feature_fields if 'feature_fields' in locals() else [],
                    "testSize": test_size if 'test_size' in locals() else 0.2,
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

    def _logistic_regression(self, X_train: np.ndarray, X_test: np.ndarray, 
                           y_train: List[float], y_test: List[float], 
                           feature_names: List[str]) -> Dict:
        """Implement logistic regression for binary classification"""
        try:
            # Validate binary target (0 or 1)
            y_train_binary = [int(y) for y in y_train]
            y_test_binary = [int(y) for y in y_test]
            
            # Check if targets are binary
            unique_train = set(y_train_binary)
            unique_test = set(y_test_binary)
            
            if not (unique_train <= {0, 1} and unique_test <= {0, 1}):
                return {
                    "status": "error",
                    "method": "logistic",
                    "message": "Logistic regression requires binary target values (0 or 1)"
                }
            
            # Check if we have both classes
            if len(unique_train) < 2:
                return {
                    "status": "error", 
                    "method": "logistic",
                    "message": "Logistic regression requires both classes (0 and 1) in training data"
                }
            
            # Fit logistic regression model
            model = LogisticRegression(random_state=42, max_iter=1000)
            model.fit(X_train, y_train_binary)
            
            # Make predictions
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)
            
            # Get probabilities
            y_prob_train = model.predict_proba(X_train)[:, 1]
            y_prob_test = model.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            accuracy_train = accuracy_score(y_train_binary, y_pred_train)
            accuracy_test = accuracy_score(y_test_binary, y_pred_test)
            
            # Calculate precision, recall, F1-score
            precision_train = precision_score(y_train_binary, y_pred_train, zero_division=0)
            precision_test = precision_score(y_test_binary, y_pred_test, zero_division=0)
            
            recall_train = recall_score(y_train_binary, y_pred_train, zero_division=0)
            recall_test = recall_score(y_test_binary, y_pred_test, zero_division=0)
            
            f1_train = f1_score(y_train_binary, y_pred_train, zero_division=0)
            f1_test = f1_score(y_test_binary, y_pred_test, zero_division=0)
            
            # Feature importance (coefficients)
            feature_importance = dict(zip(feature_names, model.coef_[0].tolist()))
            
            # Calculate class distribution
            class_distribution = {
                "train": {
                    "class_0": sum(1 for y in y_train_binary if y == 0),
                    "class_1": sum(1 for y in y_train_binary if y == 1)
                },
                "test": {
                    "class_0": sum(1 for y in y_test_binary if y == 0),
                    "class_1": sum(1 for y in y_test_binary if y == 1)
                }
            }
            
            return {
                "status": "success",
                "method": "logistic",
                "coefficients": model.coef_[0].tolist(),
                "intercept": float(model.intercept_[0]),
                "accuracy_train": float(accuracy_train),
                "accuracy_test": float(accuracy_test),
                "precision_train": float(precision_train),
                "precision_test": float(precision_test),
                "recall_train": float(recall_train),
                "recall_test": float(recall_test),
                "f1_score_train": float(f1_train),
                "f1_score_test": float(f1_test),
                "predictions_train": y_pred_train.tolist(),
                "predictions_test": y_pred_test.tolist(),
                "probabilities_train": y_prob_train.tolist(),
                "probabilities_test": y_prob_test.tolist(),
                "feature_importance": feature_importance,
                "feature_names": feature_names,
                "class_distribution": class_distribution,
                "summary": f"Logistic regression completed with accuracy = {accuracy_test:.4f}, F1-score = {f1_test:.4f}"
            }
            
        except Exception as e:
            logger.error(f"Error in logistic regression: {e}")
            return {
                "status": "error",
                "method": "logistic",
                "message": str(e)
            }