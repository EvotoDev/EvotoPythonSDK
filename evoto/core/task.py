"""Task definitions and registry."""

import logging
from typing import Any, Callable
from dataclasses import dataclass

from ._internal.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class TaskDefinition:
    """Static metadata for one plugin task."""
    name: str                           # Task name used over IPC
    func: Callable                      # Callable implementation
    inline: bool = False                # Run synchronously on the receiver
                                        # thread (skip worker pool). Use only
                                        # for fast, non-blocking callables.


class TaskRegistry:
    """Registry of tasks for the current plugin process."""

    def __init__(self):
        """Create an empty registry."""
        self._tasks: dict[str, TaskDefinition] = {}

    def register(
        self,
        func: Callable | None = None,
        *,
        name: str | None = None,
        inline: bool = False,
    ) -> Callable:
        """
        Decorator to register a task.

        Args:
            func: Supplied implicitly when used as ``@evoto.task``.
            name: Override the task name (defaults to ``func.__name__``).
            inline: When True the task runs on the SDK receiver thread
                instead of the worker pool. Use only for very fast,
                non-blocking callables (e.g. pure in-memory lookups) -
                any slow I/O or heavy compute will stall ping / events /
                other tasks. Defaults to False (pool-dispatched).

        Usage::

            @evoto.task
            def process(x: int) -> int:     # pool-dispatched (default)
                return x * 2

            @evoto.task(name="custom.name")
            def another(x):                 # pool-dispatched, custom name
                return x

            @evoto.task(inline=True)
            def status() -> str:            # runs on receiver thread
                return "ok"
        """
        def decorator(f: Callable) -> Callable:
            task_name = name or f.__name__

            if task_name in self._tasks:
                logger.warning(f"Task '{task_name}' already registered, overwriting")

            self._tasks[task_name] = TaskDefinition(
                name=task_name, func=f, inline=inline
            )
            logger.debug(
                f"Registered task: {task_name} (inline={inline})"
            )

            return f

        if func is not None:
            return decorator(func)
        return decorator

    def get(self, name: str) -> TaskDefinition | None:
        """Return task definition by name."""
        return self._tasks.get(name)

    def is_inline(self, name: str) -> bool:
        """True if the task is registered and marked ``inline``."""
        task_def = self._tasks.get(name)
        return bool(task_def and task_def.inline)

    def execute(self, name: str, params: dict[str, Any]) -> Any:
        """
        Execute a registered task.

        Args:
            name: task name.
            params: keyword args for the task callable.

        Returns:
            Whatever the task function returns.
        """
        task_def = self._tasks.get(name)
        if not task_def:
            raise TaskNotFoundError(name)

        return task_def.func(**params)

    def list_tasks(self) -> dict[str, dict[str, Any]]:
        """
        Serialize all tasks for plugin.hello.

        The host currently only consumes task names (object keys); the
        per-task object is reserved for future metadata and kept empty.
        """
        return {name: {} for name in self._tasks}
