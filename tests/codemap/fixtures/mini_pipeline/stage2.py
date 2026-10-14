# tests/codemap/fixtures/mini_pipeline/stage2.py
from tools.codemap.runtime import pipeline_stage

@pipeline_stage(
    id="mini_s2",
    order=2,
    input_model="MiniOutput",
    output_model="FinalResult",
    triggers=["auto:s1_completed"],
    upstream=["mini_s1"],
    downstream=[],
    artifacts=["output/s2.json"],
    verify_cmds=[]
)
def run_stage_two(data: str) -> dict:
    return {"result": data, "length": len(data)}
