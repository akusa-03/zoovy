from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base class for all Zoovy autonomous agents."""

    @abstractmethod
    def run(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Execute the agent given a natural language prompt."""
        pass
