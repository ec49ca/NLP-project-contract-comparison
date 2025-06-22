"""
Util dependencies for the MCP HTTP API

Contains dependency injection functions and global state management.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global instances
session_manager: Optional[Any] = None
agents: Dict[str, Any] = {}


def get_session_manager():
	"""Get the global session manager instance"""
	return session_manager


def get_agents():
	"""Get the global agents dictionary"""
	return agents


def set_session_manager(manager):
	"""Set the global session manager instance"""
	global session_manager
	session_manager = manager


def set_agents(agents_dict):
	"""Set the global agents dictionary"""
	global agents
	agents = agents_dict


async def get_initialized_server():
	"""Dependency to ensure server is initialized"""
	if not session_manager:
		raise Exception("Server not initialized")
	return True