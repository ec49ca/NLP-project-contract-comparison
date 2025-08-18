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
        Discover agent classes strictly from the public exports of the agents package.

        Only classes exported via src.agents.__all__ will be considered. This ensures
        that discovery is controlled centrally by the package API surface.

        Returns:
            A dictionary mapping export names to agent classes
        """
        self._discovered_agents = {}

        try:
            # Import the agents package
            package = importlib.import_module(self.agents_package)

            # Read the public API from __all__
            exported_names = getattr(package, "__all__", [])
            if not exported_names:
                logger.warning(
                    "No public agents exported via __all__. Nothing to discover.",
                    extra={'package': self.agents_package},
                )
                return {}

            # Pull attributes from the package and keep subclasses of AgentInterface
            for export_name in exported_names:
                try:
                    obj = getattr(package, export_name, None)
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, AgentInterface)
                        and obj is not AgentInterface
                    ):
                        self._discovered_agents[export_name] = obj
                        logger.info(
                            "Discovered agent export",
                            extra={'export_name': export_name, 'class_name': obj.__name__},
                        )
                    else:
                        logger.debug(
                            "Skipped export",
                            extra={
                                'export_name': export_name,
                                'reason': "Not an AgentInterface subclass",
                            },
                        )
                except Exception as e:
                    logger.error(
                        "Error processing export",
                        extra={
                            'export_name': export_name,
                            'package': self.agents_package,
                            'error': str(e),
                        },
                    )

            logger.info(
                "Discovered agents from exports",
                extra={'count': len(self._discovered_agents)},
            )
            return self._discovered_agents

        except Exception as e:
            logger.error("Error discovering agents from exports", extra={'error': str(e)})
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
