"""
BackgroundRunner : file de tâches asynchrones fire-and-forget.
Remplace les asyncio.gather ad hoc par un gestionnaire centralisé.
"""
import asyncio

from neo.shared.logging import technical_log


class BackgroundRunner:

    def __init__(self):
        self._tasks: set[asyncio.Task] = set()

    def submit(self, coro, name: str = "task"):
        """Lance une coroutine en background sans bloquer l'appelant."""
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task):
        self._tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            technical_log("background", f"task '{task.get_name()}' failed: {exc}")

    @property
    def pending_count(self) -> int:
        return len(self._tasks)

    async def shutdown(self):
        """Annule toutes les tâches en cours et attend leur fin."""
        if not self._tasks:
            return
        technical_log("background", f"shutting down {len(self._tasks)} tasks")
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
