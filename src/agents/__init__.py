# Re-export agent classes for discovery to pick up via __all__ attributes
from .stats.stats_agent import StatsAgent
from .weather.weather_agent import WeatherAgent
from .knowledge_graph.knowledge_graph_extraction_agent import (
    KnowledgeGraphExtractionAgent,
)

__all__ = [
    "StatsAgent",
    "WeatherAgent",
    "KnowledgeGraphExtractionAgent",
]
