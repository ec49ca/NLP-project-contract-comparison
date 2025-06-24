"""
Agent Discovery module for AgentForge.
Provides functionality to automatically discover and register agents.
"""
import importlib
import inspect
import os
import pkgutil
import sys
from typing import Dict, List, Type, Any, Optional
import logging

from ..interfaces.agent import AgentInterface

logger = logging.getLogger(__name__)

class AgentDiscovery:
    """
    Discovers and manages agent classes available in the system.
    """

    def __init__(self, agents_package="src.agents"):
        """
        Initialize the agent discovery system.

        Args:
            agents_package: The package path where agents are located
        """
        self.agents_package = agents_package
        self._discovered_agents: Dict[str, Type[AgentInterface]] = {}

    async def discover_agents(self) -> Dict[str, Type[AgentInterface]]:
        """
        Scan the agents package to find all available agent classes.

        Returns:
            A dictionary mapping agent module names to agent classes
        """
        self._discovered_agents = {}

        try:
            # Import the agents package
            package = importlib.import_module(self.agents_package)
            package_path = os.path.dirname(package.__file__) if package.__file__ else None

            if not package_path:
                logger.error(f"Could not determine package path for {self.agents_package}")
                return {}

            # Find all modules in the package
            for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
                if is_pkg:
                    continue  # Skip subpackages

                try:
                    # Import the module
                    module = importlib.import_module(f"{self.agents_package}.{module_name}")

                    # Find all classes in the module that inherit from AgentInterface
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, AgentInterface) and
                            obj != AgentInterface):

                            # Store the agent class
                            self._discovered_agents[module_name] = obj
                            logger.info(f"Discovered agent: {module_name} ({obj.__name__})")

                except Exception as e:
                    logger.error(f"Error loading agent module {module_name}: {str(e)}")

            logger.info(f"Discovered {len(self._discovered_agents)} agents")
            return self._discovered_agents

        except Exception as e:
            logger.error(f"Error discovering agents: {str(e)}")
            return {}

    def get_agent_class(self, agent_module_name: str) -> Optional[Type[AgentInterface]]:
        """
        Get an agent class by its module name.

        Args:
            agent_module_name: The name of the agent module

        Returns:
            The agent class if found, None otherwise
        """
        return self._discovered_agents.get(agent_module_name)

    def get_all_agent_classes(self) -> Dict[str, Type[AgentInterface]]:
        """
        Get all discovered agent classes.

        Returns:
            A dictionary mapping agent module names to agent classes
        """
        return self._discovered_agents
