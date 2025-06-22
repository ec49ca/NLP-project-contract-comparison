"""
Configuration for external services
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

# Validation
def validate_openai_config() -> bool:
	"""Validate OpenAI configuration"""
	logger.info("Validating OpenAI configuration...")
	logger.info(f"OPENAI_API_KEY present: {bool(OPENAI_API_KEY)}")
	logger.info(f"OPENAI_MODEL: {OPENAI_MODEL}")
	logger.info(f"OPENAI_MAX_TOKENS: {OPENAI_MAX_TOKENS}")
	logger.info(f"OPENAI_TEMPERATURE: {OPENAI_TEMPERATURE}")

	if not OPENAI_API_KEY:
		logger.error("OPENAI_API_KEY environment variable is required")
		raise ValueError("OPENAI_API_KEY environment variable is required")

	if not OPENAI_API_KEY.startswith("sk-"):
		logger.warning(f"OPENAI_API_KEY doesn't start with 'sk-': {OPENAI_API_KEY[:10]}...")

	logger.info("OpenAI configuration validation successful")
	return True