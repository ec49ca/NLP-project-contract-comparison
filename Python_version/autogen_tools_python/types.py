from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AgentContext:
    domain: Optional[str] = None        # What domain this agent specializes in
    constraints: Optional[List[str]] = None  # Special rules or constraints
    preferences: Optional[List[str]] = None  # Preferred patterns or styles
    knowledge: Optional[str] = None     # Domain-specific knowledge
