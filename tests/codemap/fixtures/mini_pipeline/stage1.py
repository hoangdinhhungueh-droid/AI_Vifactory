# tests/codemap/fixtures/mini_pipeline/stage1.py
from tools.codemap.runtime import pipeline_stage

def helper_transform(text: str) -> str:
    if not text:
        raise ValueError("Text cannot be empty")
    return text.strip().upper()

@pipeline_stage(
    id="mini_s1",
    order=1,
    input_model="MiniInput",
    output_model="MiniOutput",
    triggers=["cli:run"],
    upstream=[],
    downstream=["mini_s2"],
    artifacts=["output/s1.json"],
    verify_cmds=["pytest test_s1.py"]
)
def run_stage_one(raw: str) -> str:
    try:
        res = helper_transform(raw)
        return res
    except Exception as e:
        raise RuntimeError(f"Transform failed: {e}")
