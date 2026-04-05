"""
Abstract base class for all pipeline agents.
Every agent must implement `execute()` and can optionally override hooks.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Main execution method. Subclasses define their own kwargs."""
        ...

    async def pre_execute(self, **kwargs) -> bool:
        """Hook before execution. Return False to skip."""
        return True

    async def post_execute(self, result: Any, **kwargs) -> Any:
        """Hook after execution. Can transform the result."""
        return result

    async def on_error(self, error: Exception, **kwargs) -> None:
        """Hook for error handling."""
        self.logger.error(f"[{self.name}] Error: {error}", exc_info=True)

    async def run(self, **kwargs) -> Any:
        """Template method: pre → execute → post, with error handling."""
        start = datetime.now(timezone.utc)
        try:
            should_run = await self.pre_execute(**kwargs)
            if not should_run:
                self.logger.info(f"[{self.name}] Skipped (pre_execute returned False)")
                return None

            result = await self.execute(**kwargs)
            result = await self.post_execute(result, **kwargs)

            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            self.logger.info(f"[{self.name}] Completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            await self.on_error(e, **kwargs)
            raise
