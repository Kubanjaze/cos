"""COS batch execution engine.

Processes multiple items through an operation with progress tracking and error collection.

Usage:
    from cos.core.batch import batch_executor
    results = batch_executor.run(
        items=["file1.csv", "file2.csv"],
        operation=lambda item: ingest_file(item),
        investigation_id="inv-001",
        description="Batch ingest"
    )
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from cos.core.events import event_bus
from cos.core.logging import get_logger

logger = get_logger("cos.core.batch")

MAX_ERROR_DETAILS = 100


@dataclass
class BatchResult:
    description: str
    total: int
    succeeded: int
    failed: int
    duration_s: float
    items_per_sec: float
    errors: list[dict] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.succeeded / max(self.total, 1)


class BatchExecutor:
    """Generic batch processor with progress tracking and error collection."""

    def run(
        self,
        items: Iterable[Any],
        operation: Callable[[Any], Any],
        investigation_id: str = "default",
        description: str = "Batch operation",
        fail_fast: bool = False,
    ) -> BatchResult:
        """Process items through operation. Returns BatchResult."""
        items_list = list(items)
        total = len(items_list)

        logger.info(
            f"Batch starting: '{description}' ({total} items)",
            extra={"investigation_id": investigation_id},
        )

        succeeded = 0
        failed = 0
        errors = []
        start = time.time()

        for i, item in enumerate(items_list):
            try:
                operation(item)
                succeeded += 1
            except Exception as e:
                failed += 1
                if len(errors) < MAX_ERROR_DETAILS:
                    errors.append({"item": str(item)[:200], "error": str(e)[:200], "index": i})
                logger.warning(f"Batch item {i+1}/{total} failed: {e}")
                if fail_fast:
                    break

            # Progress event every 10% or every item if small batch
            if total <= 20 or (i + 1) % max(1, total // 10) == 0:
                event_bus.emit("batch.progress", {
                    "description": description,
                    "current": i + 1,
                    "total": total,
                    "succeeded": succeeded,
                    "failed": failed,
                    "investigation_id": investigation_id,
                })

        duration = time.time() - start
        rate = total / max(duration, 0.001)

        result = BatchResult(
            description=description,
            total=total,
            succeeded=succeeded,
            failed=failed,
            duration_s=round(duration, 3),
            items_per_sec=round(rate, 1),
            errors=errors,
        )

        logger.info(
            f"Batch complete: {succeeded}/{total} succeeded, {failed} failed, {duration:.3f}s",
            extra={"investigation_id": investigation_id},
        )

        event_bus.emit("batch.completed", {
            "description": description,
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "investigation_id": investigation_id,
        })

        return result


# Singleton
batch_executor = BatchExecutor()
