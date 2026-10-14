# Kế hoạch triển khai: QuantFlow Trade Code Map & Visual System Topology

Mình là Claude. Plan dưới đây theo đúng cấu trúc bạn yêu cầu. Lưu ý trước: mình chưa đọc được mã nguồn trong `/root/live_trade`, nên plan không chứa số dòng nào. Mọi tọa độ `file:line` phải do tool sinh ra từ AST, không được viết tay hay đoán.

## 1. Intent & Problem Framing

Vấn đề gốc không phải là "thiếu tài liệu" mà là thiếu một nguồn sự thật có thể truy vấn được, luôn khớp với code đang chạy. Tài liệu viết tay sẽ lệch khỏi code sau vài lần commit, và một bản map lệch còn nguy hiểm hơn không có map, vì nó tạo cảm giác an toàn giả.

Vì vậy thiết kế dựa trên 4 nguyên tắc:

- Sinh tự động, tất định (deterministic): phân tích tĩnh bằng `ast`, cùng input cho cùng output. Không dùng LLM để tạo tọa độ hay schema.
- Không bao giờ import module live: chỉ đọc file và parse AST. Import `quantflow.*` có thể kích hoạt side effect như kết nối sàn, khởi tạo client, hay mở socket Telegram. Đây là rủi ro lớn nhất trên VPS đang trade thật.
- Trung thực về độ chính xác: Python động (getattr, callback, `Thread(target=...)`, handler đăng ký qua decorator) khiến call graph không thể chính xác 100%. Mỗi cạnh phải có `confidence` (`exact` / `heuristic`), và các lời gọi không resolve được phải liệt kê ra, không được bỏ qua.
- Có kiểm tra độ tươi (staleness): mỗi file mang hash. Nếu map lệch với code, `check` trả exit code khác 0 và /boss không được phép dùng map cũ.

Các trade-off chính:

| Lựa chọn | Chọn | Lý do |
|---|---|---|
| AST tĩnh hay runtime tracing | AST tĩnh | Tracing yêu cầu can thiệp vào tiến trình live. Không chấp nhận được. |
| Thư viện graph (networkx, pyvis) hay stdlib | Chỉ stdlib | Không thêm dependency vào môi trường live. |
| HTML dùng CDN (D3, Cytoscape) hay tự chứa | Tự chứa, SVG + JS thuần | Dùng offline được, không rò rỉ dữ liệu qua request bên ngoài. |
| Layout tính trong JS hay Python | Python (swimlane theo zone + rank topo) | Tất định, test được, JS chỉ render. |

Điểm cần lưu ý đặc biệt là coupling qua file JSON. Bốn luồng học giao tiếp chủ yếu qua `trade_journal.json`, `shadow_trade_ledger.json`, `active_market_scenarios.json`, `forecast_quarantine_ledger.json`. Call graph sẽ không thấy được kiểu coupling này. Do đó map bắt buộc có một đồ thị dataflow riêng (ai đọc, ai ghi file nào), kèm cảnh báo khi một file có nhiều writer (rủi ro race condition và hỏng ledger).

## 2. Execution Venue Analysis

Mình không đồng ý hoàn toàn với khuyến nghị VPS_247 có sẵn. Hệ thống trade chạy 24/7, nhưng code map thì không cần LLM chạy 24/7.

Phân loại đúng là dạng lai:

- OFFLINE_LOCAL (phát triển): toàn bộ việc viết tool, test và tạo HTML. Worker làm trên một bản sao code (`rsync` từ VPS về, hoặc `git clone`), không đụng vào thư mục live trong lúc phát triển.
- VPS (chỉ phần làm mới định kỳ): một script Python tất định chạy bằng systemd timer hoặc git post-commit hook để rebuild map khi hash thay đổi. Chi phí LLM bằng 0, vì không có bước nào cần LLM.

Về yêu cầu bắt buộc dùng `claude-v4.1-flash` (fallback `claude-6-luna`) qua HHTech API cho tác vụ nền: tác vụ nền ở đây không gọi model nào cả, nên đây là phương án rẻ nhất. Nếu sau này muốn thêm tóm tắt ngôn ngữ tự nhiên cho các module không có docstring, đó có thể là một bước tùy chọn dùng `claude-v4.1-flash`, cache theo hash file, chỉ gọi khi file thay đổi. Mình chưa kiểm chứng được hai model ID này trên HHTech API, nên bạn cần xác nhận tên chính xác trước khi bật bước đó. Bước tùy chọn này cũng sẽ gửi mã nguồn trading ra endpoint bên thứ ba, nên cần bạn đồng ý rõ ràng.

Ràng buộc an toàn khi chạy trên VPS live:

- Chạy với `nice -n 19 ionice -c3` và `MemoryMax`/`CPUQuota` trong systemd unit, để không bao giờ tranh tài nguyên với vòng lặp trade.
- Chỉ ghi vào `/root/live_trade/.codemap/`. Không ghi vào cây source.
- Không đọc `.env`, credentials, hay file key. Danh sách loại trừ được hard-code.
- Không có network listener. Nếu muốn xem HTML, dùng SSH tunnel hoặc `scp` về máy, không mở cổng public. File HTML mô tả toàn bộ kiến trúc hệ thống trade, nên không được để public.

## 3. Component-by-Component Blueprint

Vị trí: `/root/live_trade/tools/trade_codemap/` (phát triển trên bản sao, deploy bằng git). Tham số `--root` cho phép chạy trên bất kỳ bản sao nào.

```
tools/
  __init__.py                    # rỗng, chỉ để chạy được python -m tools.trade_codemap
  trade_codemap/
    __init__.py
    __main__.py                  # CLI argparse, điều phối subcommand
    zones.py                     # khai báo zone, glob, sink tới hạn (dữ liệu, không có logic)
    scanner.py                   # walk file + parse AST -> Module/Symbol (có line_start/line_end)
    imports.py                   # đồ thị import, resolve alias, import tương đối
    callgraph.py                 # cạnh gọi hàm + confidence, danh sách unresolved
    entrypoints.py               # __main__, Thread/create_task, scheduler, handler Telegram
    contracts.py                 # schema In/Out từ type hint, dataclass, TypedDict, pydantic, key dict trả về
    dataflow.py                  # phát hiện đọc/ghi file JSON (open, json.load/dump, Path.read_text/write_text)
    blast.py                     # BFS ngược + phân tầng rủi ro
    layout.py                    # swimlane theo zone + rank topo, tọa độ tất định
    render_html.py               # nhúng JSON + JS/CSS inline -> trade_pipeline.html
    freshness.py                 # hash sha256 từng file, so sánh với map
    redact.py                    # lọc chuỗi giống secret khỏi output
    assets/
      viewer.js                  # renderer SVG thuần, không dependency
      viewer.css
  tests/
    test_trade_codemap.py        # test trên code thật, không mock
deploy/
  trade-codemap.service          # oneshot, nice/ionice, giới hạn tài nguyên
  trade-codemap.timer            # mỗi 15 phút, chỉ rebuild khi hash thay đổi
```

Output trong `/root/live_trade/.codemap/`:

```
trade_codemap.json        # nguồn sự thật cho /boss và Worker
trade_pipeline.html       # UI tự chứa
build_report.json         # file lỗi parse, số cạnh unresolved, thời gian build
```

### zones.py (cấu hình, phải được bạn duyệt)

```python
# Khai báo zone. Glob tính tương đối với --root.
ZONES = {
    "core_monitor": ["quantflow_live_trade_monitor.py"],
    "smc_engine":   ["quantflow/smc/**/*.py"],
    "stream1_blind_forward": ["quantflow/learning/blind_forward_learner.py"],
    "stream2_dreaming": ["quantflow/dreaming/engine.py", "quantflow/dreaming/adaptive_config.py"],
    "stream3_shadow":   ["quantflow/dreaming/shadow_ledger.py"],
    "stream4_forecast": ["quantflow/forecast/closed_loop_engine.py",
                         "quantflow/forecast/scenario_oracle.py",
                         "quantflow/forecast/radar_scheduler.py"],
    "execution":    ["quantflow/execution/**/*.py"],
    "risk_shield":  ["quantflow/rl/safety_shield.py", "**/fractional_kelly.py"],
    "telegram":     ["quantflow/telegram/**/*.py", "scripts/quantflow_telebot_daemon.py"],
}

# File dữ liệu được theo dõi như node trong dataflow graph.
DATA_FILES = [
    "trade_journal.json", "shadow_trade_ledger.json",
    "active_market_scenarios.json", "forecast_quarantine_ledger.json",
]

# Zone mà bất kỳ thay đổi nào chạm tới đều là CRITICAL.
CRITICAL_ZONES = {"execution", "risk_shield", "core_monitor"}

# Không bao giờ đọc.
EXCLUDE = [".env*", "**/*secret*", "**/*credential*", "**/*.pem", "**/*.key",
           ".git/**", ".codemap/**", "**/__pycache__/**", "venv/**", ".venv/**"]
```

Đường dẫn `fractional_kelly.py` trong yêu cầu không có thư mục rõ ràng, nên dùng glob `**/`. Worker phải xác nhận vị trí thật ở T0.

### Schema của trade_codemap.json

```json
{
  "version": 1,
  "generated_at": "ISO-8601 UTC",
  "root": "/root/live_trade",
  "git_head": "sha hoặc null",
  "files": {
    "quantflow/smc/structure.py": {"sha256": "...", "zone": "smc_engine", "parse_ok": true, "loc": 0}
  },
  "symbols": {
    "quantflow.smc.structure:detect_bos": {
      "kind": "function | async_function | method | class",
      "file": "quantflow/smc/structure.py",
      "line_start": 0,
      "line_end": 0,
      "zone": "smc_engine",
      "signature": "detect_bos(candles: list[Candle], lookback: int = 20) -> BOSResult | None",
      "contract": {
        "inputs": [{"name": "candles", "annotation": "list[Candle]", "default": null}],
        "output": {"annotation": "BOSResult | None", "dict_keys": [], "source": "annotation"},
        "raises": ["ValueError"]
      },
      "docstring_first_line": "...",
      "decorators": []
    }
  },
  "types": {
    "quantflow.smc.types:BOSResult": {
      "kind": "dataclass | TypedDict | pydantic | NamedTuple",
      "file": "...", "line_start": 0, "line_end": 0,
      "fields": [{"name": "direction", "annotation": "Literal['bull','bear']"}]
    }
  },
  "edges": {
    "imports": [{"src": "module", "dst": "module", "line": 0}],
    "calls":   [{"src": "symbol_id", "dst": "symbol_id", "line": 0, "confidence": "exact | heuristic"}],
    "unresolved_calls": [{"src": "symbol_id", "expr": "self.handler(...)", "line": 0}],
    "dataflow": [{"symbol": "symbol_id", "file": "shadow_trade_ledger.json", "mode": "read | write", "line": 0, "confidence": "exact | heuristic"}]
  },
  "entrypoints": [
    {"symbol": "symbol_id", "kind": "main | thread | asyncio_task | scheduler | telegram_handler", "line": 0}
  ],
  "warnings": [
    {"type": "multi_writer", "file": "trade_journal.json", "writers": ["symbol_id", "symbol_id"]}
  ],
  "layout": {"nodes": [{"id": "...", "x": 0, "y": 0, "lane": "smc_engine"}]}
}
```

Các số `0` ở trên chỉ là kiểu dữ liệu, không phải giá trị thật.

Quy tắc của `contracts.py`, theo thứ tự ưu tiên:

1. Type hint trên chữ ký hàm, resolve tới `types` nếu là dataclass/TypedDict/pydantic trong repo.
2. Nếu không có annotation trả về: gom các key dạng chuỗi của dict literal trong mọi lệnh `return {...}`, đánh dấu `"source": "inferred_return_dict"`.
3. Nếu vẫn không có: `"source": "unknown"`. Không bịa schema.

Quy tắc của `dataflow.py`: chỉ nhận diện khi tên file JSON xuất hiện dưới dạng hằng chuỗi hoặc hằng module được truyền vào `open`, `Path(...)`, `json.load`/`json.dump`, `read_text`/`write_text`. Mode suy ra từ tham số `"r"`/`"w"`/`"a"` hoặc từ phương thức gọi. Đường dẫn ghép động thì `confidence: heuristic`.

### blast.py: phân tầng rủi ro

Đầu vào là một file, một symbol, hoặc một khoảng `file:line`. Thuật toán:

1. Ánh xạ đầu vào sang tập symbol bị ảnh hưởng (với khoảng dòng: mọi symbol có khoảng chồng lấn).
2. BFS ngược trên `calls` và `imports` (ai phụ thuộc vào thứ này), độ sâu mặc định là 4.
3. Nếu symbol ghi một data file, thêm toàn bộ reader của file đó vào tập ảnh hưởng (coupling qua JSON).
4. Kiểm tra reachability: tập ảnh hưởng có giao với các đường đi từ entrypoint `core_monitor` hay không.

Phân tầng:

- `CRITICAL`: chạm tới `CRITICAL_ZONES`, hoặc nằm trên đường đi từ vòng lặp live tới việc đặt lệnh.
- `HIGH`: chạm tới một data file dùng chung bởi nhiều stream, hoặc có entrypoint thread/scheduler bị ảnh hưởng.
- `MEDIUM`: chỉ ảnh hưởng trong nội bộ một zone học.
- `LOW`: không có dependent nào.

Output luôn kèm số lượng `unresolved_calls` trong vùng ảnh hưởng, để người đọc biết mức độ mù còn lại.

### CLI

```bash
python -m tools.trade_codemap build   [--root PATH]
python -m tools.trade_codemap check   # exit 0 nếu map khớp hash, 3 nếu cũ
python -m tools.trade_codemap locate  <symbol|pattern>        # -> file:line_start-line_end
python -m tools.trade_codemap contract <symbol>                # -> In/Out schema
python -m tools.trade_codemap blast   <file|symbol|file:L1-L2> [--depth N]
python -m tools.trade_codemap flow    <live|stream1|stream2|stream3|stream4|telegram>
python -m tools.trade_codemap datafile <name.json>             # -> reader/writer + cảnh báo
python -m tools.trade_codemap html                             # -> .codemap/trade_pipeline.html
```

Mọi subcommand đều hỗ trợ `--json` để /boss và Worker parse bằng máy.

### trade_pipeline.html

- Một file duy nhất, JSON nhúng trong `<script type="application/json">`, JS/CSS inline, không có bất kỳ `http(s)://` nào trong `src`/`href`.
- Swimlane theo zone: Core Monitor, SMC, Risk Shield, Execution, Stream 1 đến 4, Telegram. Data file hiển thị dạng node riêng nối bằng nét đứt.
- Click vào node để mở panel hiển thị `file:line`, contract, caller/callee, nút "Blast radius" tô sáng vùng ảnh hưởng theo tầng rủi ro.
- Bộ lọc theo zone, ô tìm kiếm, bật/tắt cạnh `heuristic`.
- Accessibility: có danh sách dạng bảng song song với SVG, điều hướng được bằng bàn phím, `aria-label` trên node, tầng rủi ro dùng cả ký hiệu và chữ chứ không chỉ màu. Để xác nhận tuân thủ WCAG đầy đủ, cần kiểm thử thủ công với công cụ hỗ trợ và đánh giá chuyên gia.

### Tích hợp vào /boss

Thêm một gate bắt buộc vào prompt /boss cho mọi tác vụ có từ khóa trading:

1. Chạy `check`. Nếu exit khác 0 thì chạy `build` trước.
2. Chạy `locate` cho mọi symbol nhắc tới trong yêu cầu, và `blast` cho mọi file dự định sửa.
3. Dán output `--json` vào phần "Component Blueprint" của plan. Plan nào không có tọa độ lấy từ tool thì bị coi là không hợp lệ.
4. Nếu blast trả `CRITICAL`, plan phải có bước xác nhận của người dùng trước khi deploy, và phải có bước rollback.

## 4. Task Decomposition cho Worker (Gemini 3.8 Flash High)

Tất cả làm trên bản sao local, trừ T13.

- T0. Khảo sát. Input: bản sao repo. Output: `build_report` sơ bộ gồm danh sách file thật trong mỗi glob ở `zones.py`, phiên bản Python trên VPS (`python3 --version`), xác nhận vị trí `fractional_kelly.py`. Báo cáo glob nào không khớp file nào.
- T1. `zones.py` và `redact.py`. Output: hằng cấu hình như trên. `redact.py` có hàm `is_excluded(path)` và `redact(text)` (che các chuỗi giống API key, token, private key).
- T2. `scanner.py`. Input: root. Output: `dict[file -> {sha256, zone, parse_ok, symbols[]}]`. Dùng `ast.parse`, `node.lineno`, `node.end_lineno`, tính cả decorator vào `line_start`. Phương thức đặt ID dạng `module:Class.method`. File parse lỗi thì ghi vào report, không làm crash.
- T3. `imports.py`. Output: cạnh import, xử lý `from . import x`, `import a.b as c`, và bảng alias theo từng module.
- T4. `callgraph.py`. Output: `calls` và `unresolved_calls`. Resolve được: tên hàm trong cùng module, tên đã import, `module.func`, `self.method` trong cùng class, `ClassName(...)` thành `__init__`. Còn lại vào danh sách unresolved.
- T5. `entrypoints.py`. Phát hiện `if __name__ == "__main__"`, `threading.Thread(target=X)`, `asyncio.create_task(X(...))`, `loop.run_until_complete`, đăng ký kiểu `schedule.every`/APScheduler, handler Telegram (`add_handler`, decorator `@...message_handler`). Đây cũng là nơi tạo cạnh `confidence: heuristic` từ entrypoint tới target.
- T6. `contracts.py`. Áp dụng 3 quy tắc ưu tiên ở trên, trích xuất `types` từ dataclass, TypedDict, NamedTuple, lớp con `BaseModel`.
- T7. `dataflow.py`. Output: cạnh `dataflow` và cảnh báo `multi_writer`.
- T8. `blast.py`. Output: tập ảnh hưởng, tầng rủi ro, các zone bị chạm, số unresolved.
- T9. `freshness.py` và lệnh `check`. Exit 0 nếu tất cả hash khớp, exit 3 nếu có thay đổi, in danh sách file lệch.
- T10. `__main__.py`. Nối toàn bộ subcommand, `--json`, ghi nguyên tử (`tmp` rồi `os.replace`) vào `.codemap/`.
- T11. `layout.py`, `assets/viewer.js`, `render_html.py`. Output: `trade_pipeline.html` tự chứa.
- T12. `tests/test_trade_codemap.py`. Viết theo mục 5, chạy trên bản sao repo thật.
- T13. Deploy lên VPS (cần bạn xác nhận). Commit trên branch mới, pull trên VPS, cài `deploy/trade-codemap.{service,timer}`, chạy `build` một lần, kiểm tra tiến trình live không bị ảnh hưởng. Đây là thay đổi trên máy production, nên Worker phải dừng lại chờ bạn đồng ý trước bước này.
- T14. Cập nhật prompt /boss với gate ở mục 3.

## 5. Verification Protocol & Acceptance Criteria

Mọi kiểm tra chạy trên mã nguồn thật của QuantFlow, không dùng fixture giả hay mock.

### Lệnh kiểm tra

```bash
# 1. Biên dịch
python3 -m py_compile tools/trade_codemap/*.py

# 2. Test trên code thật
python3 -m pytest tools/tests/test_trade_codemap.py -v

# 3. Gọi trực tiếp, mỗi lệnh phải exit 0
python3 -m tools.trade_codemap build --root "$ROOT"
python3 -m tools.trade_codemap check --root "$ROOT"
python3 -m tools.trade_codemap flow live --json --root "$ROOT"
python3 -m tools.trade_codemap datafile shadow_trade_ledger.json --json --root "$ROOT"
python3 -m tools.trade_codemap blast quantflow/rl/safety_shield.py --json --root "$ROOT"
python3 -m tools.trade_codemap html --root "$ROOT"
```

### Test bắt buộc trong test_trade_codemap.py

- Không import code live: sau khi `build`, `sys.modules` không được chứa key nào bắt đầu bằng `quantflow`. Đây là test quan trọng nhất.
- Tọa độ chính xác: với mỗi symbol, đọc lại các dòng `line_start..line_end` từ file thật. Dòng đầu (sau decorator) phải chứa `def <name>`, `async def <name>` hoặc `class <name>`.
- Phủ toàn bộ: số `FunctionDef`/`AsyncFunctionDef`/`ClassDef` đếm độc lập bằng `ast.walk` phải bằng số symbol trong map, với mọi file `parse_ok`.
- Phủ zone: mỗi zone trong `zones.py` có ít nhất một file. Nếu không, test fail và in tên zone.
- Data file: mỗi file trong `DATA_FILES` có ít nhất một reader hoặc writer. Nếu không, test fail để buộc người đọc kiểm tra lại (có thể tên file được ghép động).
- Tất định: chạy `build` hai lần, so sánh output sau khi bỏ `generated_at`, phải giống hệt từng byte.
- Staleness: copy repo sang thư mục tạm, sửa một file, `check` phải trả exit 3. Sau đó xóa thư mục tạm.
- Blast: blast trên một file thuộc `risk_shield` phải trả tầng `CRITICAL`.
- HTML: parse bằng `html.parser`, JSON nhúng phải `json.loads` được, không có chuỗi `http://` hay `https://` trong thuộc tính `src`/`href`.
- Không rò rỉ: output không chứa đường dẫn nào khớp `EXCLUDE`, và `redact()` không phát hiện thêm chuỗi giống secret nào.
- Phạm vi ghi: sau `build`, chỉ có thay đổi trong `.codemap/` (so sánh `git status --porcelain`).

### Kiểm tra riêng trên VPS (T13)

- Trước và sau `build`: `systemctl status` của service trade, PID không đổi, không có restart.
- `build` hoàn thành dưới 30 giây, RSS đỉnh dưới 300 MB (đo bằng `/usr/bin/time -v`). Hai ngưỡng này là giá trị mặc định mình chọn, bạn có thể chỉnh.
- Timer chạy 2 chu kỳ, `journalctl -u trade-codemap` không có lỗi, và chu kỳ không có thay đổi hash thì bỏ qua rebuild.

### Tiêu chí chấp nhận

- Toàn bộ test pass, mọi lệnh trong mục kiểm tra exit 0 (riêng test staleness kỳ vọng exit 3).
- `build_report.json` nêu rõ số `unresolved_calls`. Con số này không cần bằng 0, nhưng phải được báo cáo và hiển thị trong mọi output `blast`.
- /boss từ chối tạo plan cho tác vụ trading khi không có output `locate`/`blast` từ tool.

Những điều plan này chưa xác minh được: cấu trúc file thật trong `/root/live_trade`, phiên bản Python trên VPS, repo có dùng git hay không, và cách các stream thực sự đọc/ghi JSON. T0 tồn tại để chốt các điểm này trước khi viết code.