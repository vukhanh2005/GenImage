from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable[[Callable[[str], None]], Any]) -> None:
        super().__init__()
        self.task = task

    def run(self) -> None:
        try:
            result = self.task(self.progress.emit)
            self.succeeded.emit(result)
        except Exception as exc:
            traceback.print_exc()
            self.failed.emit(str(exc) or exc.__class__.__name__)

