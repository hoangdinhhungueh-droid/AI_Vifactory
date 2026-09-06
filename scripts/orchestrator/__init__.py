"""scripts/orchestrator — Multi-Agent Orchestration Framework & Tooling (R1).

Production orchestration engine for AI Video Factory (VF Pipeline B1 to B3.5).
Provides decoupled task partitioning, process lifecycle management, sandboxed
resource recycling per Rule 119, and Rule 128 governance guarding against
semantic bias.
"""

from .rule128_governor import (
    Rule128Governor,
    Rule128ViolationError,
    validate_generic_task_id,
)
from .resource_recycler import (
    ResourceSandbox,
    ResourceRecycler,
    get_system_temp_dir,
)
from .lifecycle_manager import (
    LifecycleManager,
    SubprocessWorker,
    WorkerResult,
)
from .task_partitioner import (
    TaskPartitioner,
    PipelineStage,
    StageContract,
    PIPELINE_STAGES,
)
from .runner import OrchestratorRunner, main

__version__ = "1.0.0"
__all__ = [
    "OrchestratorRunner",
    "TaskPartitioner",
    "PipelineStage",
    "StageContract",
    "PIPELINE_STAGES",
    "LifecycleManager",
    "SubprocessWorker",
    "WorkerResult",
    "ResourceSandbox",
    "ResourceRecycler",
    "get_system_temp_dir",
    "Rule128Governor",
    "Rule128ViolationError",
    "validate_generic_task_id",
    "main",
]
