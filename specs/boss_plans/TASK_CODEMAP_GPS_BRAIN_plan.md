# IMPLEMENTATION PLAN: Code Map & Visual Pipeline Traceability

Lưu ý trước: tôi chưa đọc codebase AI Video Factory, nên tên thư mục (`src/`, `tools/`) và tên stage dưới đây là giả định. Task T0 là bước khảo sát bắt buộc để xác nhận lại trước khi Worker viết code. Rule 121/127 được hiểu theo mô tả của bạn: xác minh bằng lệnh chạy thật và không dùng mock.

## 1. Intent & Problem Framing

### Vấn đề gốc

Ba nỗi đau thực chất là ba lớp thông tin khác nhau, và mỗi lớp cần một cơ chế riêng:

| Lớp | Câu hỏi | Cơ chế |
|---|---|---|
| Static (cấu trúc) | Stage nằm ở file nào, hàm nào gọi hàm nào, schema in/out là gì | AST scanner + Pydantic introspection → `codemap.json` |
| Runtime (thực thi) | Lần chạy này, stage X nhận gì, trả gì, ghi artifact nào, lỗi ở đâu | Decorator `@pipeline_stage` → `events.jsonl` theo từng run |
| Lineage (pháp y duyệt) | Dữ liệu User/Agent chốt có thực sự vào stage kế tiếp không | Hash từng field của payload duyệt, so với input thực tế của stage sau |

Thiếu một lớp nào thì hệ thống vẫn mù. Code map tĩnh không trả lời được "dữ liệu duyệt có bị ghi đè không". Trace runtime không cho biết "sửa hàm này thì gãy ai".

### Mức chi tiết Opus cần

Opus cần đủ để đi từ triệu chứng đến dòng code mà không grep. Chia 4 tầng, đọc từ trên xuống, dừng khi đủ:

- L0: danh sách stage theo thứ tự, entrypoint, trạng thái handoff tổng (khoảng 1 màn hình)
- L1: hợp đồng từng stage: file:line, input/output model, trigger, artifact, failure modes, lệnh verify
- L2: symbol graph: mọi hàm/class trong phạm vi pipeline, `calls` và `called_by`, file:line_start-line_end
- L3: bằng chứng runtime: run gần nhất, hash, diff lineage (nằm ở file riêng theo run, chỉ đọc khi debug)

L0 đến L2 nằm trong một file duy nhất. L3 tách ra vì nó tăng theo số lần chạy.

### Trade-off chính

- Nguồn sự thật cho thứ tự stage: AST không suy ra được orchestration đáng tin (gọi động, queue, retry). Chọn khai báo bằng decorator `@pipeline_stage(...)` ngay trong code, scanner đọc tham số decorator qua AST. Sự thật nằm cạnh code, không có file YAML bị bỏ quên.
- Import để lấy JSON schema của Pydantic có thể gây side effect (kết nối DB, load model). Chạy introspection trong subprocess có timeout, chỉ import module chứa model. Nếu import fail, ghi `schema_status: "UNRESOLVED"` thay vì crash.
- Kích thước `codemap.json`: giới hạn L2 vào các symbol có thể với tới từ entrypoint (reachable), không index toàn bộ thư viện. Mục tiêu dưới 300 KB.
- Payload lớn (frame, audio, video): không snapshot nội dung, chỉ lưu path + sha256 + bytes.
- Tracer không bao giờ được làm hỏng pipeline: mọi lỗi trong tracer bị bắt, ghi warning, stage vẫn chạy.
- Bí mật: snapshot phải redact key khớp `api_key|token|secret|password|authorization`.

## 2. Execution Venue Analysis

Venue: `OFFLINE_LOCAL`. Xác nhận khuyến nghị.

- Toàn bộ việc xây dựng (scanner, builder, UI, test) là phát triển cục bộ trong Antigravity IDE bởi Worker Gemini 3.8 Flash High.
- Tracer runtime sẽ chạy ở bất cứ đâu pipeline chạy, kể cả VPS. Tuy nhiên tracer không gọi LLM nào: chỉ hash và ghi JSONL. Vì vậy quy định gọi `claude-v4.1-flash` / fallback `claude-6-luna` qua HHTech API không áp dụng.
- Nếu sau này muốn có bot Telegram tóm tắt lineage DRIFT tự động 24/7, đó là task VPS_247 riêng và khi đó mới áp dụng quy định model chi phí thấp.

## 3. Component-by-Component Blueprint

### Cấu trúc file

```
tools/codemap/
  __init__.py
  __main__.py          # CLI: build | check | where | trace | lineage | ui
  schema.py            # Pydantic models cho registry, event, approval, lineage
  hashing.py           # canonical JSON, sha256, flatten field paths, redact
  ast_scanner.py       # parse .py, symbols, call graph, decorator args, raise/except
  introspect.py        # subprocess: import model → model_json_schema()
  handoff.py           # so producer.output vs consumer.input
  builder.py           # ghép tất cả → .codemap/codemap.json
  runtime.py           # @pipeline_stage, run context, events.jsonl
  approval.py          # record_approval()
  lineage.py           # approval vs consumed input → verdict theo field
  ui/
    template.html      # vanilla JS + SVG, không CDN
    render.py          # nhúng JSON vào HTML → .codemap/pipeline.html
tests/codemap/
  fixtures/mini_pipeline/   # pipeline thật 3 stage, model thật, file thật
  test_hashing.py
  test_ast_scanner.py
  test_handoff.py
  test_runtime_lineage.py
  test_builder_repo.py      # chạy trên repo thật
.codemap/
  codemap.json              # L0-L2, commit vào git
  runs/<run_id>/events.jsonl
  runs/<run_id>/approvals.jsonl
  runs/<run_id>/snapshots/<stage_id>.{in,out}.json
  pipeline.html             # sinh ra, không commit
```

`.codemap/runs/` và `pipeline.html` vào `.gitignore`. `codemap.json` được commit để Opus đọc được ngay khi mở repo.

### Contract: `codemap.json`

```python
# tools/codemap/schema.py (trích)
from typing import Literal
from pydantic import BaseModel, Field

HandoffStatus = Literal["MATCH", "PARTIAL", "MISMATCH", "UNRESOLVED"]

class SourceRef(BaseModel):
    file: str            # đường dẫn tương đối từ repo root
    line_start: int
    line_end: int

class FailureMode(BaseModel):
    exc_type: str        # "ValueError", "httpx.TimeoutException"
    origin: Literal["raise", "except", "declared"]
    ref: SourceRef
    note: str | None = None

class Stage(BaseModel):
    id: str              # "script_gen", ổn định, dùng làm khóa
    name: str
    order: int
    qualname: str        # "src.stages.script.generate_script"
    ref: SourceRef
    input_model: str | None    # "src.models.ScriptRequest"
    output_model: str | None
    triggers: list[str]        # ["cli:run", "approval:storyboard", "cron:daily"]
    upstream: list[str]
    downstream: list[str]
    artifacts: list[str]       # pattern: "output/{run_id}/script.json"
    failure_modes: list[FailureMode]
    verify_cmds: list[str]

class Symbol(BaseModel):
    qualname: str
    kind: Literal["function", "method", "class", "async_function"]
    ref: SourceRef
    decorators: list[str]
    calls: list[str]           # qualname đã resolve, hoặc "?name" nếu không resolve được
    called_by: list[str]
    stage_id: str | None       # symbol thuộc stage nào (theo reachability)

class FieldIssue(BaseModel):
    path: str                  # JSON pointer: "/scenes/0/duration"
    kind: Literal["missing_in_producer", "type_mismatch", "required_not_provided", "extra_ignored"]
    detail: str

class Handoff(BaseModel):
    from_stage: str
    to_stage: str
    producer_model: str | None
    consumer_model: str | None
    status: HandoffStatus
    issues: list[FieldIssue]

class Entrypoint(BaseModel):
    name: str                  # "cli:main", "telegram:on_approve"
    qualname: str
    ref: SourceRef

class CodemapRegistry(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: str          # ISO8601 UTC
    git_commit: str | None
    source_hash: str           # sha256 trên toàn bộ .py được scan
    summary: dict              # L0: số stage, số MISMATCH, entrypoints
    entrypoints: list[Entrypoint]
    stages: list[Stage]
    handoffs: list[Handoff]
    models: dict[str, dict]    # qualname → JSON schema (đã rút gọn $defs)
    symbols: dict[str, Symbol]
```

Thứ tự key trong file cố định (summary → entrypoints → stages → handoffs → models → symbols) để Opus đọc phần đầu là có L0/L1.

### Contract: runtime event và approval

```python
class ArtifactRef(BaseModel):
    path: str
    sha256: str
    bytes: int

class StageEvent(BaseModel):
    run_id: str
    seq: int
    stage_id: str
    ts_start: str
    ts_end: str | None
    status: Literal["OK", "ERROR", "SKIPPED"]
    input_hash: str | None
    output_hash: str | None
    input_field_hashes: dict[str, str]     # path → sha256
    output_field_hashes: dict[str, str]
    input_snapshot: str | None             # path tới snapshot đã redact
    output_snapshot: str | None
    artifacts: list[ArtifactRef]
    approval_refs: list[str]               # approval_id đã áp vào input
    error: dict | None                     # {type, message, traceback_tail}
    code_ref: SourceRef                    # file:line lúc chạy
    git_commit: str | None

class Approval(BaseModel):
    approval_id: str
    run_id: str
    target_stage: str                      # stage sẽ tiêu thụ dữ liệu này
    actor: Literal["user", "agent"]
    channel: str                           # "chat", "telegram", "ide"
    ts: str
    payload_hash: str
    field_hashes: dict[str, str]
    payload_snapshot: str

class FieldVerdict(BaseModel):
    path: str
    verdict: Literal["CARRIED", "MODIFIED", "DROPPED", "DEFAULTED", "ADDED"]
    approved_hash: str | None
    consumed_hash: str | None
    note: str | None

class LineageReport(BaseModel):
    run_id: str
    approval_id: str
    target_stage: str
    overall: Literal["INTACT", "DRIFT", "NOT_CONSUMED"]
    fields: list[FieldVerdict]
```

Quy tắc verdict:
- `CARRIED`: hash field giống nhau
- `MODIFIED`: có ở cả hai, hash khác
- `DROPPED`: có trong approval, không có trong input đã tiêu thụ
- `DEFAULTED`: hash khác approval và giá trị bằng đúng default của Pydantic field. Đây là trường hợp "bị ghi đè bởi giá trị mặc định"
- `ADDED`: có trong input nhưng không có trong approval (thông tin, không phải lỗi)
- `NOT_CONSUMED`: stage đích không có event nào tham chiếu approval_id này. Đây là trường hợp "bị bypass ngầm"

`overall = INTACT` khi chỉ có CARRIED/ADDED.

### Decorator runtime

```python
@pipeline_stage(
    id="storyboard",
    order=3,
    input_model=StoryboardRequest,
    output_model=Storyboard,
    triggers=["approval:script"],
    artifacts=["output/{run_id}/storyboard.json"],
)
def build_storyboard(req: StoryboardRequest) -> Storyboard: ...
```

Hành vi:
- Không có run context active: chạy hàm bình thường, không ghi gì (an toàn cho unit test và gọi lẻ)
- Có context: hash input, snapshot đã redact, chạy hàm, hash output, quét artifact path pattern, ghi một dòng JSONL (append + flush, an toàn khi crash giữa chừng)
- Hỗ trợ cả sync và async
- Exception của hàm gốc luôn được re-raise sau khi ghi event ERROR

Approval nối vào stage qua `apply_approval(approval_id, model_instance)` hoặc truyền `approval_id` vào run context; stage event ghi lại `approval_refs`.

### UI: `pipeline.html`

Một file HTML tự chứa, mở bằng `file://`, không CDN, không server.

- Panel trái: DAG SVG, node xếp theo `order`, cạnh là handoff. Node có badge trạng thái handoff và trạng thái run (OK/ERROR/SKIPPED). Trạng thái hiển thị bằng cả icon + chữ, không chỉ màu.
- Panel phải (khi chọn node): file:line với link `vscode://file/<abs>:<line>`, input/output schema dạng cây, callers/callees, failure modes, verify commands (nút copy).
- Thanh trên: chọn run_id. Khi có run, node hiển thị thời lượng, hash rút gọn, artifact.
- Tab Lineage: chọn approval → bảng field với verdict, giá trị approved và consumed song song (đã redact).
- Tab Handoffs: danh sách MISMATCH/PARTIAL với issue cụ thể.
- Accessibility: điều hướng node bằng Tab/Arrow, `role="button"` + `aria-label` trên node, `aria-live` cho panel chi tiết, tương phản đạt mức AA. Cần kiểm tra thủ công bằng screen reader để xác nhận đầy đủ.

### CLI

```
python -m tools.codemap build                 # sinh codemap.json
python -m tools.codemap check                 # exit 1 nếu stale hoặc có MISMATCH
python -m tools.codemap where <name>          # file:line, callers, stage
python -m tools.codemap trace <run_id>        # in event theo thứ tự
python -m tools.codemap lineage <run_id>      # in LineageReport, exit 2 nếu DRIFT
python -m tools.codemap ui [--run <run_id>]   # sinh pipeline.html
```

## 4. Task Decomposition cho Worker (Gemini 3.8 Flash High)

Mỗi task kết thúc bằng lệnh verify của nó. Không chuyển task khi verify chưa exit 0.

T0. Khảo sát (read-only)
- Input: repo root
- Việc: liệt kê entrypoint (`if __name__ == "__main__"`, CLI, handler bot/webhook), hàm orchestrator, Pydantic model, nơi xử lý approval từ chat, thư mục output artifact
- Output: `.codemap/inventory.json` dạng `{entrypoints, candidate_stages, models, approval_handlers, artifact_dirs}` kèm file:line. Báo lại cho Boss danh sách stage đề xuất trước khi T5
- Verify: `python -c "import json;json.load(open('.codemap/inventory.json'))"`

T1. `schema.py`
- Input: contract ở mục 3
- Output: toàn bộ model, có `model_config = ConfigDict(extra="forbid")`
- Verify: `python -m py_compile tools/codemap/schema.py`

T2. `hashing.py`
- Hàm: `canonical_json(obj) -> bytes` (sort_keys, separators `(",",":")`, ensure_ascii=False, float qua `repr`, datetime ISO, Path → str, BaseModel → `model_dump(mode="json")`); `sha256_of(obj)`; `flatten(obj) -> dict[path, value]` theo JSON pointer; `field_hashes(obj)`; `redact(obj)`
- Verify: `pytest tests/codemap/test_hashing.py` gồm: thứ tự key khác cho cùng hash, list khác thứ tự cho hash khác, redact thay giá trị bằng `"***"`, unicode tiếng Việt ổn định

T3. `ast_scanner.py`
- Dùng `ast` stdlib. Với mỗi file: module qualname, function/class/method, line range, decorator (dạng chuỗi), call trong thân hàm. Resolve call qua import alias của module; không resolve được thì ghi `?name`
- Đọc tham số `@pipeline_stage(...)` bằng `ast.literal_eval` cho literal và tên dạng dotted cho model
- Thu `raise X` và `except X` thành FailureMode
- Tính `called_by` bằng đảo ngược graph; tính reachability từ entrypoint
- Bỏ qua `venv`, `.venv`, `site-packages`, `__pycache__`, `node_modules`
- Verify: `pytest tests/codemap/test_ast_scanner.py` trên fixture mini_pipeline, assert đúng số stage, đúng cạnh call, đúng line

T4. `introspect.py`
- Chạy `subprocess.run([sys.executable, "-c", ...], timeout=30)`, import model theo qualname, in `model_json_schema()` và danh sách default theo field
- Lỗi import → `UNRESOLVED` + stderr rút gọn
- Verify: test trên model thật trong fixture

T5. `runtime.py` + gắn decorator vào stage thật
- Viết `run_context(run_id)` (contextvars), `@pipeline_stage`
- Sau khi Boss duyệt danh sách stage từ T0, gắn decorator vào từng stage trong `src/`. Không đổi logic stage
- Verify: `python -m py_compile` trên mọi file đã sửa; chạy test hiện có của dự án, phải pass như trước

T6. `handoff.py`
- So `output_model` của upstream với `input_model` của downstream qua JSON schema: field required của consumer không có ở producer → `required_not_provided`; cùng tên khác type → `type_mismatch`; producer có mà consumer không nhận → `extra_ignored`
- Status: không issue → MATCH; chỉ `extra_ignored` → PARTIAL; còn lại → MISMATCH; thiếu schema → UNRESOLVED
- Verify: fixture có một cặp cố tình lệch, assert MISMATCH đúng path

T7. `builder.py` + CLI `build`/`check`
- Ghép T3, T4, T6 → `CodemapRegistry`, validate bằng chính model rồi ghi file với `indent=1`
- `check`: tính lại `source_hash`, khác với file → exit 1 "STALE"; có MISMATCH → exit 1
- Verify: `python -m tools.codemap build && python -m tools.codemap check; echo $?` trên repo thật

T8. `approval.py`
- `record_approval(run_id, target_stage, payload, actor, channel) -> approval_id`
- Tích hợp vào handler duyệt ở chat/bot tìm được ở T0: gọi `record_approval` ngay tại điểm chốt dữ liệu, trước khi giao cho stage kế tiếp
- Verify: chạy handler thật với payload thật trong fixture, file `approvals.jsonl` có dòng hợp lệ

T9. `lineage.py` + CLI `lineage`
- Đọc approvals và events của run, ghép theo `approval_refs` và `target_stage`, tính FieldVerdict theo quy tắc mục 3, dùng default từ T4 để phát hiện DEFAULTED
- Verify: `test_runtime_lineage.py` chạy mini_pipeline thật 3 lần:
  1. luồng đúng → INTACT
  2. stage 2 cố tình bỏ một field → DROPPED
  3. stage 2 khởi tạo model mới thay vì dùng payload duyệt → DEFAULTED
  4. stage đích không nhận approval → NOT_CONSUMED

T10. `ui/template.html` + `render.py` + CLI `ui`
- Nhúng codemap và (tùy chọn) dữ liệu run vào `<script type="application/json" id="data">`, escape `</` để tránh vỡ HTML
- Không dùng `innerHTML` với dữ liệu từ payload; dùng `textContent` để tránh XSS từ nội dung người dùng
- Verify: `python -m tools.codemap ui --run <run_id>`; test parse HTML bằng `html.parser`, assert JSON nhúng load được và số node bằng số stage

T11. CLI `where` và `trace`
- `where`: tìm exact qualname, sau đó suffix match; in file:line, stage, callers, callees
- Verify: chạy với một hàm thật của repo, exit 0, output chứa đường dẫn tồn tại

T12. Tích hợp quy trình agent
- Thêm vào file rules của agent trong repo: "Trước khi sửa code, đọc `.codemap/codemap.json`. Sau khi sửa, chạy `python -m tools.codemap build && python -m tools.codemap check`."
- Thêm pre-commit hook (tùy chọn) chạy `check`
- Verify: hook chạy được trên commit thử ở branch riêng

T13. E2E trên pipeline thật
- Chạy một run thật của AI Video Factory với input nhỏ, có ít nhất một bước duyệt
- Sinh codemap, trace, lineage, UI
- Output: run_id, kết quả lineage, số MISMATCH thực tế báo về Boss

## 5. Verification Protocol & Acceptance Criteria

### Lệnh bắt buộc (tất cả exit 0)

```bash
python -m py_compile tools/codemap/*.py tools/codemap/ui/render.py
pytest tests/codemap -q
python -m tools.codemap build
python -m tools.codemap check
python -m tools.codemap where <một_stage_thật>
python -m tools.codemap trace <run_id_thật>
python -m tools.codemap ui --run <run_id_thật>
```

`python -m tools.codemap lineage <run_id>` exit 0 khi INTACT, exit 2 khi DRIFT. Test fixture phải xác nhận cả hai mã thoát.

### Zero-Mock

- Không `unittest.mock`, không `MagicMock`, không monkeypatch hàm stage. Kiểm tra bằng `grep -rn "mock" tests/codemap` phải rỗng
- Fixture `mini_pipeline` là code Python thật, model Pydantic thật, ghi file thật vào `tmp_path`
- `test_builder_repo.py` chạy builder trên chính repo, không trên dữ liệu giả

### Acceptance Criteria

1. Mọi stage từ T0 có trong `codemap.json` với `ref.file` tồn tại và `line_start` trỏ đúng dòng `def`
2. Mọi cặp upstream/downstream có Handoff với status khác rỗng; MISMATCH liệt kê field path cụ thể
3. `check` phát hiện stale: sửa một file `.py` bất kỳ mà không build lại → exit 1
4. Lineage phát hiện đúng 4 kịch bản ở T9, không false positive ở kịch bản INTACT
5. Snapshot không chứa giá trị của key nhạy cảm (test assert trên file thật)
6. Tracer lỗi (ví dụ thư mục run không ghi được) không làm stage fail; stage vẫn trả kết quả đúng
7. Overhead tracer dưới 5% thời gian stage với payload dưới 1 MB (đo trên fixture)
8. `codemap.json` dưới 300 KB trên repo thật; nếu vượt, báo Boss để quyết định tách symbols
9. `pipeline.html` mở offline, điều hướng được bằng bàn phím, chọn node hiển thị file:line và schema
10. Test suite sẵn có của dự án vẫn pass sau khi gắn decorator

### Điểm Worker phải dừng và báo Boss

- T0 không tìm thấy ranh giới stage rõ ràng (orchestrator kiểu một hàm khổng lồ): cần quyết định tách stage trước khi gắn decorator
- Approval handler nằm ở service khác hoặc chạy trên VPS: cần thống nhất nơi ghi `approvals.jsonl`
- Import model gây side effect nặng khiến T4 UNRESOLVED trên phần lớn model