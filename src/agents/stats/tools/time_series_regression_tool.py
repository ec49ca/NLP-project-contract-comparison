import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings

warnings.filterwarnings("ignore")


class TimeSeriesRegressionTool:
    """
    Time Series Regression Tool for forecasting and analysis.

    Methods supported:
    - ARIMA and SARIMA (manual or auto via pmdarima when available)
    - Exponential Smoothing (Holt-Winters)
    - STL decomposition for trend/seasonality/residuals

    Inputs:
    - data: list[dict] with a time field and a numeric value field
      - timeField should be ISO strings aligned to frequency, e.g., monthly-start 'YYYY-MM-01' with frequency='MS'
      - valueField should be numeric (int/float)
    - frequency: must match input granularity. Common values: 'D' (daily), 'W' (weekly), 'M' (month-end), 'MS' (monthly-start).

    Requirements for seasonal models:
    - SARIMA and seasonal Exponential Smoothing require at least 2 full seasonal cycles for stable fitting
      (e.g., with monthly seasonality period=12, provide >= 24 months).

    Outputs:
    - Forecast mean and confidence intervals (where available)
    - Diagnostics: AIC/BIC, RMSE/MAE, Ljung-Box residual autocorrelation test
    - Decomposition components (trend, seasonal, residual) via STL
    """

    def __init__(self):
        self.name = "time_series_regression"
        self.description = (
            "Perform time series regression analysis and forecasting using various methods "
            "including ARIMA, SARIMA, STL decomposition, and Exponential Smoothing"
        )

    def convert_numpy_types(self, obj):
        """Convert numpy/pandas types to Python native types for JSON serialization"""
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, (pd.Series,)):
            return obj.dropna().tolist()
        if isinstance(obj, (pd.DataFrame,)):
            return obj.dropna().to_dict("records")
        if isinstance(obj, dict):
            return {k: self.convert_numpy_types(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.convert_numpy_types(v) for v in obj]
        return obj

    def _prepare_time_series_data(
        self, data: List[Dict], time_field: str, value_field: str, frequency: str = "D"
    ) -> pd.Series:
        """Prepare time series data from input"""
        df = pd.DataFrame(data)
        df[time_field] = pd.to_datetime(df[time_field])
        df = df.sort_values(time_field).set_index(time_field)
        ts = df[value_field].asfreq(frequency, method=None)
        if ts.isnull().any():
            ts = ts.interpolate(method="time")
        return ts

    def _check_stationarity(self, ts: pd.Series) -> Dict[str, Any]:
        """ADF-like stationarity summary via rolling stats and simple heuristic"""
        window = max(5, min(24, max(5, len(ts) // 10)))
        rolling_mean = ts.rolling(window=window).mean()
        rolling_std = ts.rolling(window=window).std()
        cv = float(rolling_std.mean() / rolling_mean.abs().mean()) if rolling_mean.abs().mean() else 0.0
        return {
            "window": window,
            "rolling_mean": self.convert_numpy_types(rolling_mean),
            "rolling_std": self.convert_numpy_types(rolling_std),
            "coefficient_of_variation": cv,
            "is_stationary": cv < 0.5,
        }

    def _stl_decompose(self, ts: pd.Series, period: Optional[int]) -> Dict[str, Any]:
        try:
            from statsmodels.tsa.seasonal import STL  # lazy import
            if not period:
                # Heuristic for period
                period = 12 if len(ts) >= 24 else max(2, min(7, len(ts) // 2))
            stl = STL(ts, period=period, robust=True)
            res = stl.fit()
            return {
                "trend": self.convert_numpy_types(res.trend),
                "seasonal": self.convert_numpy_types(res.seasonal),
                "residual": self.convert_numpy_types(res.resid),
                "observed": self.convert_numpy_types(ts),
                "period": period,
            }
        except Exception as e:
            return {"error": "STL decomposition failed", "details": str(e)}

    def _fit_arima_or_sarima(
        self,
        ts: pd.Series,
        order: tuple,
        seasonal_order: Optional[tuple] = None,
        forecast_steps: Optional[int] = None,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        try:
            if seasonal_order:
                from statsmodels.tsa.statespace.sarimax import SARIMAX  # lazy import
                model = SARIMAX(
                    ts,
                    order=order,
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
            else:
                from statsmodels.tsa.arima.model import ARIMA  # lazy import
                model = ARIMA(ts, order=order)

            fitted = model.fit()

            steps = forecast_steps if forecast_steps is not None else min(12, max(1, len(ts) // 4))
            alpha = max(0.0, min(1.0, 1.0 - confidence_level))
            forecast_res = fitted.get_forecast(steps=steps)
            forecast_mean = forecast_res.predicted_mean
            conf_int = forecast_res.conf_int(alpha=alpha)

            fitted_values = fitted.fittedvalues
            common_index = fitted_values.index.intersection(ts.index)
            mse = mean_squared_error(ts.loc[common_index], fitted_values.loc[common_index])
            mae = mean_absolute_error(ts.loc[common_index], fitted_values.loc[common_index])

            residuals = ts - fitted_values.reindex(ts.index, method="nearest")
            try:
                from statsmodels.stats.diagnostic import acorr_ljungbox  # lazy import
                lb = acorr_ljungbox(
                    residuals.dropna(),
                    lags=min(10, max(1, len(residuals.dropna()) - 1)),
                    return_df=True,
                )
                lb_stat = self.convert_numpy_types(lb["lb_stat"]) if not lb.empty else None
                lb_p = self.convert_numpy_types(lb["lb_pvalue"]) if not lb.empty else None
            except Exception:
                lb_stat, lb_p = None, None

            return {
                "model_type": "SARIMA" if seasonal_order else "ARIMA",
                "order": order,
                "seasonal_order": seasonal_order,
                "aic": float(getattr(fitted, "aic", np.nan)),
                "bic": float(getattr(fitted, "bic", np.nan)),
                "fitted_values": self.convert_numpy_types(fitted_values),
                "forecast": {
                    "mean": self.convert_numpy_types(forecast_mean),
                    "lower": self.convert_numpy_types(conf_int.iloc[:, 0]),
                    "upper": self.convert_numpy_types(conf_int.iloc[:, 1]),
                },
                "residuals": self.convert_numpy_types(residuals),
                "mse": float(mse),
                "mae": float(mae),
                "rmse": float(np.sqrt(mse)),
                "ljung_box_test": {"statistic": lb_stat, "p_value": lb_p},
                "model_summary": str(fitted.summary()),
            }
        except Exception as e:
            return {"error": "ARIMA/SARIMA fitting failed", "details": str(e)}

    def _fit_exponential_smoothing(
        self,
        ts: pd.Series,
        trend: Optional[str] = "add",
        seasonal: Optional[str] = "add",
        seasonal_periods: Optional[int] = None,
        forecast_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing  # lazy import
            if seasonal_periods is None:
                seasonal_periods = 12 if len(ts) >= 24 else max(2, min(7, len(ts) // 2))
            model = ExponentialSmoothing(ts, trend=trend, seasonal=seasonal, seasonal_periods=seasonal_periods)
            fitted = model.fit()

            steps = forecast_steps if forecast_steps is not None else min(12, max(1, len(ts) // 4))
            forecast = fitted.forecast(steps)

            fitted_values = fitted.fittedvalues
            common_index = fitted_values.index.intersection(ts.index)
            mse = mean_squared_error(ts.loc[common_index], fitted_values.loc[common_index])
            mae = mean_absolute_error(ts.loc[common_index], fitted_values.loc[common_index])

            return {
                "model_type": "ExponentialSmoothing",
                "trend": trend,
                "seasonal": seasonal,
                "seasonal_periods": seasonal_periods,
                "aic": float(getattr(fitted, "aic", np.nan)),
                "bic": float(getattr(fitted, "bic", np.nan)),
                "fitted_values": self.convert_numpy_types(fitted_values),
                "forecast": {"mean": self.convert_numpy_types(forecast)},
                "mse": float(mse),
                "mae": float(mae),
                "rmse": float(np.sqrt(mse)),
            }
        except Exception as e:
            return {"error": "Exponential Smoothing fitting failed", "details": str(e)}

    def _auto_arima(
        self,
        ts: pd.Series,
        seasonal: bool = True,
        m: int = 12,
        forecast_steps: Optional[int] = None,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        try:
            from pmdarima import auto_arima  # lazy import
            model = auto_arima(
                ts,
                seasonal=seasonal,
                m=m,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                with_intercept=True,
            )
            order = model.order
            seasonal_order = model.seasonal_order if seasonal else None
            return self._fit_arima_or_sarima(
                ts,
                order,
                seasonal_order,
                forecast_steps=forecast_steps,
                confidence_level=confidence_level,
            )
        except Exception as e:
            return {"error": "Auto ARIMA failed", "details": str(e)}

    async def execute_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            data = request.get("data", [])
            time_field = request.get("timeField", "date")
            value_field = request.get("valueField", "value")
            method = request.get("method", "auto_arima")
            frequency = request.get("frequency", "D")
            # Optional validation controls
            test_horizon = request.get("testHorizon")  # optional int, last N points as holdout
            confidence_level = float(request.get("confidenceLevel", 0.95))

            order = tuple(request.get("order", (1, 1, 1)))
            seasonal_order = request.get("seasonalOrder")
            if seasonal_order is not None:
                seasonal_order = tuple(seasonal_order)
            trend = request.get("trend", "add")
            seasonal = request.get("seasonal", "add")
            seasonal_periods = request.get("seasonalPeriods")
            m = int(request.get("seasonalPeriod", seasonal_periods or 12))

            if not data:
                return {"status": "error", "result": "No data provided", "matched_kwargs": request, "summary": "No data provided"}

            if time_field not in data[0] or value_field not in data[0]:
                return {
                    "status": "error",
                    "result": f"Required fields '{time_field}' and '{value_field}' not found in data",
                    "matched_kwargs": request,
                    "summary": "Missing required fields",
                }

            ts = self._prepare_time_series_data(data, time_field, value_field, frequency)

            stationarity = self._check_stationarity(ts)
            decomposition = self._stl_decompose(ts, seasonal_periods)

            # Optional time-based holdout for out-of-sample metrics
            ts_train = ts
            ts_test = None
            if isinstance(test_horizon, int) and test_horizon > 0 and test_horizon < len(ts):
                ts_train = ts.iloc[:-test_horizon]
                ts_test = ts.iloc[-test_horizon:]

            if method == "auto_arima":
                model_result = self._auto_arima(
                    ts_train,
                    seasonal=seasonal is not None and seasonal != "none",
                    m=m,
                    forecast_steps=(len(ts_test) if ts_test is not None else None),
                    confidence_level=confidence_level,
                )
            elif method == "arima":
                model_result = self._fit_arima_or_sarima(
                    ts_train,
                    order,
                    forecast_steps=(len(ts_test) if ts_test is not None else None),
                    confidence_level=confidence_level,
                )
            elif method == "sarima":
                if seasonal_order is None:
                    seasonal_order = (1, 1, 1, m)
                model_result = self._fit_arima_or_sarima(
                    ts_train,
                    order,
                    seasonal_order,
                    forecast_steps=(len(ts_test) if ts_test is not None else None),
                    confidence_level=confidence_level,
                )
            elif method == "exponential_smoothing":
                model_result = self._fit_exponential_smoothing(
                    ts_train,
                    trend,
                    seasonal,
                    seasonal_periods,
                    forecast_steps=(len(ts_test) if ts_test is not None else None),
                )
            else:
                return {"status": "error", "result": f"Unknown method: {method}", "matched_kwargs": request, "summary": f"Unknown method: {method}"}

            if "error" in model_result:
                return {"status": "error", "result": model_result["error"], "matched_kwargs": request, "summary": model_result["error"]}

            # Compute out-of-sample metrics if holdout is provided and forecast available
            oos_metrics = None
            if ts_test is not None:
                try:
                    fc = model_result.get("forecast", {})
                    fc_mean = fc.get("mean")
                    if fc_mean is not None:
                        y_true = pd.Series(ts_test.values)
                        y_pred = pd.Series(fc_mean)
                        if len(y_true) == len(y_pred):
                            mse = mean_squared_error(y_true, y_pred)
                            mae = mean_absolute_error(y_true, y_pred)
                            oos_metrics = {
                                "horizon": int(test_horizon),
                                "rmse": float(np.sqrt(mse)),
                                "mae": float(mae),
                                "confidenceLevel": confidence_level,
                            }
                except Exception:
                    oos_metrics = None

            result = {
                "method": method,
                "time_series_info": {
                    "length": len(ts),
                    "frequency": frequency,
                    "start_date": str(ts.index[0]),
                    "end_date": str(ts.index[-1]),
                    "missing_values": int(ts.isnull().sum()),
                },
                "stationarity": stationarity,
                "decomposition": decomposition,
                "model_results": model_result,
                "out_of_sample": oos_metrics,
            }

            summary = (
                f"Time series regression using {method}. "
                f"AIC: {model_result.get('aic', 'N/A')}, RMSE: {model_result.get('rmse', 'N/A')}. "
                f"Holdout: {oos_metrics if oos_metrics else 'none'}"
            )
            return {"status": "success", "result": self.convert_numpy_types(result), "matched_kwargs": request, "summary": summary}
        except Exception as e:
            logger.error("Time series regression failed", extra={'error': str(e), 'request': request})
            return {"status": "error", "result": f"Time series regression failed: {e}", "matched_kwargs": request, "summary": str(e)}
