"""
Options Agent - Black-Scholes Option Pricing Implementation

This agent provides options pricing capabilities using the Black-Scholes model.
It calculates call and put option prices along with the Greeks (delta, gamma, theta, vega, rho).

## Core Tools:
1. calculate_option_price - Calculate call/put prices using Black-Scholes
2. calculate_greeks - Calculate option Greeks
3. calculate_implied_volatility - Calculate implied volatility from option price
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
import uuid
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize_scalar

from ..interfaces.agent import AgentInterface

logger = logging.getLogger(__name__)

class OptionsAgent(AgentInterface):
	"""Options pricing agent using Black-Scholes model"""

	def __init__(self):
		self._agent_id_str = "options"
		self._uuid = None
		self._name = "Options Pricing Agent"
		self._description = "Calculate option prices and Greeks using Black-Scholes model"
		self._initialized = False

	@property
	def agent_id_str(self) -> str:
		return self._agent_id_str

	@property
	def uuid(self) -> UUID:
		if self._uuid is None:
			raise ValueError("UUID has not been set yet.")
		return self._uuid

	@uuid.setter
	def uuid(self, value: UUID):
		if self._uuid is not None:
			raise ValueError("UUID can only be set once.")
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
		self._initialized = True
		logger.info("OptionsAgent initialized successfully")

	async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Process incoming requests through the agent."""
		if not self._initialized:
			return {"error": "Agent not initialized"}

		command = request.get("command", "")

		if command == "calculate_option_price":
			return await self._calculate_option_price(request)
		elif command == "calculate_greeks":
			return await self._calculate_greeks(request)
		elif command == "calculate_implied_volatility":
			return await self._calculate_implied_volatility(request)
		elif command == "calculate_all":
			return await self._calculate_all(request)
		else:
			return {
				"error": f"Unknown command: {command}",
				"available_commands": [
					"calculate_option_price",
					"calculate_greeks",
					"calculate_implied_volatility",
					"calculate_all"
				]
			}

	async def _calculate_option_price(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Calculate option prices using Black-Scholes model."""
		try:
			# Extract parameters
			S = request.get("spot_price")  # Current stock price
			K = request.get("strike_price")  # Strike price
			T = request.get("time_to_expiry")  # Time to expiry (in years)
			r = request.get("risk_free_rate")  # Risk-free rate
			sigma = request.get("volatility")  # Volatility
			option_type = request.get("option_type", "both")  # "call", "put", or "both"

			# Validate inputs
			if any(param is None for param in [S, K, T, r, sigma]):
				return {"error": "Missing required parameters: spot_price, strike_price, time_to_expiry, risk_free_rate, volatility"}

			if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
				return {"error": "All parameters must be positive"}

			# Calculate option prices
			if option_type in ["call", "both"]:
				call_price = self._black_scholes_call(S, K, T, r, sigma)
			else:
				call_price = None

			if option_type in ["put", "both"]:
				put_price = self._black_scholes_put(S, K, T, r, sigma)
			else:
				put_price = None

			result = {
				"status": "success",
				"data": {
					"spot_price": S,
					"strike_price": K,
					"time_to_expiry": T,
					"risk_free_rate": r,
					"volatility": sigma,
					"option_type": option_type
				}
			}

			if call_price is not None:
				result["data"]["call_price"] = call_price
			if put_price is not None:
				result["data"]["put_price"] = put_price

			return result

		except Exception as e:
			logger.error(f"Error calculating option price: {str(e)}")
			return {
				"status": "error",
				"message": f"Error calculating option price: {str(e)}"
			}

	async def _calculate_greeks(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Calculate option Greeks."""
		try:
			# Extract parameters
			S = request.get("spot_price")
			K = request.get("strike_price")
			T = request.get("time_to_expiry")
			r = request.get("risk_free_rate")
			sigma = request.get("volatility")
			option_type = request.get("option_type", "both")

			# Validate inputs
			if any(param is None for param in [S, K, T, r, sigma]):
				return {"error": "Missing required parameters: spot_price, strike_price, time_to_expiry, risk_free_rate, volatility"}

			if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
				return {"error": "All parameters must be positive"}

			# Calculate Greeks
			if option_type in ["call", "both"]:
				call_greeks = self._calculate_call_greeks(S, K, T, r, sigma)
			else:
				call_greeks = None

			if option_type in ["put", "both"]:
				put_greeks = self._calculate_put_greeks(S, K, T, r, sigma)
			else:
				put_greeks = None

			result = {
				"status": "success",
				"data": {
					"spot_price": S,
					"strike_price": K,
					"time_to_expiry": T,
					"risk_free_rate": r,
					"volatility": sigma,
					"option_type": option_type
				}
			}

			if call_greeks is not None:
				result["data"]["call_greeks"] = call_greeks
			if put_greeks is not None:
				result["data"]["put_greeks"] = put_greeks

			return result

		except Exception as e:
			logger.error(f"Error calculating Greeks: {str(e)}")
			return {
				"status": "error",
				"message": f"Error calculating Greeks: {str(e)}"
			}

	async def _calculate_implied_volatility(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Calculate implied volatility from option price."""
		try:
			# Extract parameters
			S = request.get("spot_price")
			K = request.get("strike_price")
			T = request.get("time_to_expiry")
			r = request.get("risk_free_rate")
			option_price = request.get("option_price")
			option_type = request.get("option_type")  # "call" or "put"

			# Validate inputs
			if any(param is None for param in [S, K, T, r, option_price, option_type]):
				return {"error": "Missing required parameters: spot_price, strike_price, time_to_expiry, risk_free_rate, option_price, option_type"}

			if S <= 0 or K <= 0 or T <= 0 or option_price <= 0:
				return {"error": "All parameters must be positive"}

			if option_type not in ["call", "put"]:
				return {"error": "option_type must be 'call' or 'put'"}

			# Calculate implied volatility
			implied_vol = self._calculate_implied_volatility_bisection(
				S, K, T, r, option_price, option_type
			)

			return {
				"status": "success",
				"data": {
					"spot_price": S,
					"strike_price": K,
					"time_to_expiry": T,
					"risk_free_rate": r,
					"option_price": option_price,
					"option_type": option_type,
					"implied_volatility": implied_vol
				}
			}

		except Exception as e:
			logger.error(f"Error calculating implied volatility: {str(e)}")
			return {
				"status": "error",
				"message": f"Error calculating implied volatility: {str(e)}"
			}

	async def _calculate_all(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Calculate both option prices and Greeks."""
		try:
			# Extract parameters
			S = request.get("spot_price")
			K = request.get("strike_price")
			T = request.get("time_to_expiry")
			r = request.get("risk_free_rate")
			sigma = request.get("volatility")

			# Validate inputs
			if any(param is None for param in [S, K, T, r, sigma]):
				return {"error": "Missing required parameters: spot_price, strike_price, time_to_expiry, risk_free_rate, volatility"}

			if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
				return {"error": "All parameters must be positive"}

			# Calculate everything
			call_price = self._black_scholes_call(S, K, T, r, sigma)
			put_price = self._black_scholes_put(S, K, T, r, sigma)
			call_greeks = self._calculate_call_greeks(S, K, T, r, sigma)
			put_greeks = self._calculate_put_greeks(S, K, T, r, sigma)

			return {
				"status": "success",
				"data": {
					"spot_price": S,
					"strike_price": K,
					"time_to_expiry": T,
					"risk_free_rate": r,
					"volatility": sigma,
					"call_price": call_price,
					"put_price": put_price,
					"call_greeks": call_greeks,
					"put_greeks": put_greeks
				}
			}

		except Exception as e:
			logger.error(f"Error calculating all: {str(e)}")
			return {
				"status": "error",
				"message": f"Error calculating all: {str(e)}"
			}

	def _black_scholes_call(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
		"""Calculate call option price using Black-Scholes formula."""
		d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
		d2 = d1 - sigma * np.sqrt(T)

		call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
		return call_price

	def _black_scholes_put(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
		"""Calculate put option price using Black-Scholes formula."""
		d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
		d2 = d1 - sigma * np.sqrt(T)

		put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
		return put_price

	def _calculate_call_greeks(self, S: float, K: float, T: float, r: float, sigma: float) -> Dict[str, float]:
		"""Calculate call option Greeks."""
		d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
		d2 = d1 - sigma * np.sqrt(T)

		# Delta
		delta = norm.cdf(d1)

		# Gamma
		gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

		# Theta
		theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) -
				r * K * np.exp(-r * T) * norm.cdf(d2)) / 365  # Per day

		# Vega
		vega = S * np.sqrt(T) * norm.pdf(d1) / 100  # Per 1% change in volatility

		# Rho
		rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100  # Per 1% change in interest rate

		return {
			"delta": delta,
			"gamma": gamma,
			"theta": theta,
			"vega": vega,
			"rho": rho
		}

	def _calculate_put_greeks(self, S: float, K: float, T: float, r: float, sigma: float) -> Dict[str, float]:
		"""Calculate put option Greeks."""
		d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
		d2 = d1 - sigma * np.sqrt(T)

		# Delta
		delta = norm.cdf(d1) - 1

		# Gamma (same as call)
		gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

		# Theta
		theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) +
				r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365  # Per day

		# Vega (same as call)
		vega = S * np.sqrt(T) * norm.pdf(d1) / 100  # Per 1% change in volatility

		# Rho
		rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100  # Per 1% change in interest rate

		return {
			"delta": delta,
			"gamma": gamma,
			"theta": theta,
			"vega": vega,
			"rho": rho
		}

	def _calculate_implied_volatility_bisection(self, S: float, K: float, T: float, r: float,
											   option_price: float, option_type: str) -> float:
		"""Calculate implied volatility using bisection method."""
		def objective(sigma):
			if option_type == "call":
				return self._black_scholes_call(S, K, T, r, sigma) - option_price
			else:
				return self._black_scholes_put(S, K, T, r, sigma) - option_price

		# Initial bounds for volatility
		sigma_min, sigma_max = 0.001, 5.0

		# Bisection method
		tolerance = 1e-6
		max_iterations = 100

		for _ in range(max_iterations):
			sigma_mid = (sigma_min + sigma_max) / 2
			f_mid = objective(sigma_mid)

			if abs(f_mid) < tolerance:
				return sigma_mid

			f_min = objective(sigma_min)
			if f_min * f_mid < 0:
				sigma_max = sigma_mid
			else:
				sigma_min = sigma_mid

		return sigma_mid  # Return best approximation

	async def shutdown(self) -> None:
		"""Clean up resources when shutting down."""
		self._initialized = False
		logger.info("OptionsAgent shutdown successfully")

	def get_capabilities(self) -> List[Dict[str, Any]]:
		"""Return agent's capabilities."""
		return [
			{
				"name": "calculate_option_price",
				"description": "Calculate call and/or put option prices using Black-Scholes model",
				"parameters": {
					"spot_price": "float - Current stock price",
					"strike_price": "float - Strike price",
					"time_to_expiry": "float - Time to expiry in years",
					"risk_free_rate": "float - Risk-free interest rate",
					"volatility": "float - Volatility",
					"option_type": "string - 'call', 'put', or 'both' (default: 'both')"
				}
			},
			{
				"name": "calculate_greeks",
				"description": "Calculate option Greeks (delta, gamma, theta, vega, rho)",
				"parameters": {
					"spot_price": "float - Current stock price",
					"strike_price": "float - Strike price",
					"time_to_expiry": "float - Time to expiry in years",
					"risk_free_rate": "float - Risk-free interest rate",
					"volatility": "float - Volatility",
					"option_type": "string - 'call', 'put', or 'both' (default: 'both')"
				}
			},
			{
				"name": "calculate_implied_volatility",
				"description": "Calculate implied volatility from option price",
				"parameters": {
					"spot_price": "float - Current stock price",
					"strike_price": "float - Strike price",
					"time_to_expiry": "float - Time to expiry in years",
					"risk_free_rate": "float - Risk-free interest rate",
					"option_price": "float - Observed option price",
					"option_type": "string - 'call' or 'put'"
				}
			},
			{
				"name": "calculate_all",
				"description": "Calculate both option prices and Greeks",
				"parameters": {
					"spot_price": "float - Current stock price",
					"strike_price": "float - Strike price",
					"time_to_expiry": "float - Time to expiry in years",
					"risk_free_rate": "float - Risk-free interest rate",
					"volatility": "float - Volatility"
				}
			}
		]

	def get_status(self) -> Dict[str, Any]:
		"""Return agent's current status."""
		return {
			"agent_id": str(self.uuid) if self._uuid else None,
			"name": self._name,
			"status": "initialized" if self._initialized else "uninitialized",
			"capabilities": self.get_capabilities()
		}