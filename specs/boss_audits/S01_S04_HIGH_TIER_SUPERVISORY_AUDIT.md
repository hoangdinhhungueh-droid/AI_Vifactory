# ⚖️ BÁO CÁO NGHIỆM THU CỦA LLM CẤP CAO (HIGH-TIER SUPERVISORY AUDIT)

- **Giám sát viên (Supervisor Model)**: `gpt-6.1-sol` (qua HHTech API Gateway)
- **Thời điểm kiểm định**: 2026-11-11 02:32:25
- **Thời gian phản hồi (Latency)**: 114.49s
- **Tập phim nghiệm thu**: `KR_EP0007_jeonse_deposit_trap`

---

# KẾT LUẬN ĐIỀU HÀNH

**Verdict: CHƯA ĐẠT — REVISE. Không nên chuyển sang S05.**

Các sửa đổi ở commit cho thấy hệ thống đã vượt qua một số lỗi cục bộ nghiêm trọng: shadow script đã bị loại bỏ, dữ liệu grounding được nối vào S01–S03, invalidation được mở rộng, và đã có language gate. Tuy nhiên, **runtime artifact thực tế của S03 vẫn thất bại ở tầng nội dung cốt lõi**. S04 đang xác nhận rằng script đúng hình thức, không chứng minh rằng script đúng đề tài, đúng bằng chứng, đúng cấu trúc điều tra hay có giá trị biên tập.

---

# CÂU HỎI 1 — CODE ĐÃ MANG TÍNH HỆ THỐNG VÀ “SẠCH” CHƯA?

## 1. DAG invalidation: đã tiến bộ, nhưng chưa đủ bằng chứng để tuyên bố sạch tuyệt đối

Việc `core/run_manifest.py` tự động unlink các secondary exports:

- `spoken_script.txt`
- `director_plan.json`
- `bulk_image_prompts.txt`
- `images_manifest.json`

khi stage cha được chạy lại là đúng hướng. Nó xử lý được lỗi **split-brain artifact**: manifest nói một phiên bản, còn các file phụ vẫn chứa đầu ra của phiên bản cũ.

Runtime mới cũng xác nhận một điểm quan trọng:

> `s05..s11: pending (đã bị invalidate sạch sẽ, không còn split-brain)`

Điều này chứng minh cơ chế đã hoạt động trong trường hợp kiểm thử hiện tại.

Tuy nhiên, từ thông tin cung cấp chưa thể kết luận DAG invalidation đã hoàn chỉnh ở cấp hệ thống. Còn ít nhất bốn điểm phải được kiểm tra trực tiếp trong code:

1. **Có invalidate theo toàn bộ hậu duệ của stage cha hay chỉ theo danh sách file cố định?**  
   Việc unlink bốn file root là cần thiết nhưng chưa đồng nghĩa với việc mọi artifact downstream trong thư mục stage, cache, index hoặc metadata đều bị vô hiệu hóa.

2. **Có kiểm tra generation/run ID của artifact không?**  
   Unlink là biện pháp vật lý. Cơ chế mạnh hơn phải gắn artifact với `source_stage_hash`, `run_id`, hoặc dependency fingerprint để phát hiện artifact cũ ngay cả khi file không bị xóa.

3. **Có xử lý lỗi giữa chừng không?**  
   Nếu invalidate đã xóa file nhưng stage mới thất bại, manifest phải phản ánh trạng thái `invalidated` hoặc `failed`, không được để hệ thống coi output cũ là hợp lệ.

4. **Có kiểm tra secondary exports được tạo ở vị trí khác không?**  
   Danh sách hardcode bốn tên file có thể trở thành điểm mù khi S05–S11 tạo thêm các export tương tự.

**Đánh giá:** đạt mức **cải thiện kiến trúc**, chưa đủ dữ liệu để cấp chứng nhận “DAG sạch tuyệt đối”.

---

## 2. Recon Bridge: đã thoát khỏi hardcode KR cũ, nhưng chưa chứng minh được độ trung lập ngữ nghĩa

S02 hiện đã nạp `grounding_intel.json`, trích xuất thực thể động và loại bỏ factsheet cứng:

> `"22조 원 전세사기 HUG/MOLIT"`

S01 cũng lấy động `money_at_stake_usd` từ grounding thay vì dùng con số cố định. Đây là thay đổi đúng về mặt kiến trúc: dữ liệu sự kiện được đưa từ upstream vào pipeline thay vì cấy trực tiếp vào stage.

Tuy nhiên, artifact S03 cho thấy **Recon Bridge mới chỉ truyền được dữ liệu theo nghĩa kỹ thuật, chưa truyền được dữ liệu theo nghĩa biên tập**.

Evidence Ledger có các claim rất cụ thể:

- ngày pre-application: **10/11/2026**
- ngày có hiệu lực pháp lý: **13/11/2026**
- mức bảo đảm tối thiểu: **1/3 tiền đặt cọc**
- số nạn nhân được công nhận ở Gyeonggi: **9.317**
- các chủ thể: MOLIT, cơ quan bảo lãnh, proxy landlords, “Villa Kings”

Nhưng không một chi tiết nào xuất hiện trong `spoken_script.txt`.

Đây là dấu hiệu hệ thống **đã kết nối dữ liệu nhưng chưa bắt buộc sử dụng dữ liệu**. Một bridge chỉ thật sự đạt khi nó bảo đảm:

- claim được chọn có mặt trong nội dung;
- claim có mức ưu tiên;
- claim bị bỏ qua phải có lý do;
- claim quan trọng không bị thay bằng các câu văn tổng quát vô danh.

Hiện tại, S03 có thể nhận `grounding_intel.json` nhưng vẫn sản xuất một bài viết gần như có thể dùng cho bất kỳ vụ bê bối tài chính nào. Đó là lỗi **semantic bypass**, không phải lỗi truyền file.

---

## 3. Multi-Market Localization: khung có tính mở rộng, nhưng chưa chứng minh được bản địa hóa thực chất

Các thay đổi được mô tả là hợp lý:

- ma trận legal qualifiers cho KR, JA, VN, EN;
- thuật toán chọn một legal status cao nhất:
  `charged > alleged > settled`;
- generic multi-market template;
- đồng bộ word/character budget.

Điểm tích cực là hệ thống không còn gắn toàn bộ logic vào một câu chuyện Hàn Quốc duy nhất. Về thiết kế, việc tách:

- market;
- language;
- legal status;
- duration;
- word/character budget;
- template

là hướng đúng cho Rule 132 — **Decoupled Engine**.

Nhưng mức sẵn sàng thực tế hiện mới ở mức:

| Thị trường | Đánh giá |
|---|---|
| KR | Có thể chạy pipeline, nhưng chất lượng runtime hiện tại không đạt |
| JA | Chưa chứng minh được: thiếu artifact tiếng Nhật, thiếu test ngữ pháp/kính ngữ/legal terminology |
| VN | Chưa chứng minh được: thiếu test dấu tiếng Việt, tên cơ quan, thuật ngữ pháp lý và nhịp đọc |
| EN | Có vẻ được coi là default dễ nhất, nhưng chưa có bằng chứng test độc lập |

Một ma trận qualifier không đồng nghĩa với localization hoàn chỉnh. Localization còn phải xử lý:

- tên cơ quan bản địa;
- cấu trúc câu và trật tự thông tin;
- hệ đo lường;
- cách biểu đạt tiền;
- cách mô tả cáo buộc;
- quy tắc gọi tên cá nhân và tổ chức;
- tokenization và speech-rate;
- ngưỡng ngôn ngữ;
- văn phong phóng sự của từng thị trường.

Do đó, chưa thể nói “đã sẵn sàng mở rộng JA/VN/EN”. Có thể nói chính xác hơn:

> **Engine đã có xu hướng multi-market; nhưng chỉ KR được chạy thực tế, và ngay ở KR semantic quality vẫn thất bại.**

---

## 4. Language Gate: có thực chất ở mức nhiễm ngôn ngữ, nhưng quá hẹp

Gate:

> `target_market_language_compliance` — VETO nếu non-EN chứa >15% tiếng Anh

là một chốt chặn hữu ích, nhưng không phải language compliance đầy đủ.

Nó phát hiện được một số lỗi như:

- script KR/VN/JA bị trộn quá nhiều tiếng Anh;
- prompt rác từ SEC/Mỹ;
- thuật ngữ tiếng Anh bị lọt vào văn bản.

Nhưng nó không phát hiện được:

1. **Sai ngôn ngữ nhưng không phải tiếng Anh**  
   Ví dụ script KR chứa tiếng Nhật hoặc tiếng Trung.

2. **Câu vô nghĩa nhưng thuần tiếng Hàn**  
   Artifact hiện tại chính là ví dụ: văn bản chủ yếu là tiếng Hàn, nhưng generic và không bám đề tài.

3. **Dịch máy sai ngữ cảnh**  
   Tỷ lệ ký tự Hàn đúng không bảo đảm thuật ngữ pháp lý đúng.

4. **Lẫn tên riêng và thuật ngữ kỹ thuật không được phép**  
   Ngưỡng 15% có thể cho phép một lượng lớn từ ngoại lai ở những vị trí quan trọng.

5. **Ngôn ngữ đúng nhưng register sai**  
   Văn phong truyền hình điều tra, văn phong pháp lý, văn phong clickbait và văn phong báo cáo đều có thể cùng “đúng tiếng Hàn”.

6. **Sai tokenization theo thị trường**  
   Cách tính từ tiếng Anh trên tiếng Hàn không tương đương với cách tính contamination trên tiếng Nhật hoặc tiếng Việt.

Ngoài ra, trong artifact được cung cấp, **không thấy từ tiếng Anh rõ ràng, không thấy SEC, không thấy rác kiểm dịch thực phẩm**. Vì vậy, gate có vẻ đã vượt qua trường hợp này. Nhưng đó chỉ là bằng chứng rằng script sạch về mặt bề mặt, không phải bằng chứng gate kiểm tra toàn diện.

---

## 5. Hardcode và vi phạm Rule 128 / Rule 132

Dựa trên diff và artifact được cung cấp:

- Hardcode cũ `"22조"` / `"전세"` đã được loại bỏ khỏi S01–S02.
- Shadow script tĩnh dài khoảng 150 dòng đã được xóa khỏi S03.
- Generic template đã được đưa vào.

Đây là dấu hiệu đã thoát khỏi bẫy sửa riêng cho `KR_EP0007` ở tầng mã nguồn cơ bản.

Nhưng vẫn còn hai biểu hiện của **semantic bias**:

### a. Template vẫn có thể đang ép mọi câu chuyện vào một kịch bản khủng hoảng giống nhau

Artifact S03 dùng chuỗi câu như:

- “광범위한 구조적 충격”
- “치명적인 구조적 취약성”
- “제도적 맹점”
- “전례 없는 규모의 부실 노출”
- “막대한 유동성이 증발”
- “전면 개입”
- “전례 없는 제도 개선안”

Đây là ngôn ngữ khủng hoảng tổng quát. Nó có thể được sinh ra từ template generic, nhưng generic theo kiểu này vẫn tạo **bias về thể loại và kết luận**: mọi đề tài đều bị ép thành một vụ sụp đổ hệ thống.

### b. Decoupling mới dừng ở tách dữ liệu, chưa tách được lập luận

Một engine decoupled phải cho phép:

- grounding quyết định sự kiện;
- claim priority quyết định điểm nhấn;
- legal status quyết định qualifier;
- market profile quyết định cách trình bày;
- story structure quyết định nhịp;
- template chỉ cung cấp hình thức.

Trong artifact hiện tại, template dường như đang chi phối nội dung mạnh hơn evidence. Đây là vi phạm Rule 132 ở tầng vận hành, dù code đã được tách module.

**Kết luận cho Câu 1:**  
**Kiến trúc đã được sửa theo hướng hệ thống, nhưng chưa đạt “clean pass”.** Không còn bằng chứng rõ ràng về hardcode KR cũ, nhưng còn bằng chứng mạnh về **template semantic bias** và **grounding không được chuyển hóa thành nội dung bắt buộc**.

---

# CÂU HỎI 2 — CHẠY LẠI ĐÃ ĐẠT CHẤT LƯỢNG CHƯA?

## 1. Độ thuần tiếng Hàn

Về bề mặt, script đạt yêu cầu tương đối tốt:

- toàn bộ nội dung là tiếng Hàn;
- không thấy từ tiếng Anh đáng kể;
- không thấy “SEC” hoặc dấu vết Mỹ;
- không thấy rác kiểm dịch thực phẩm;
- không thấy đoạn prompt hoặc metadata lọt vào spoken text.

Vì vậy, `target_market_language_compliance = true` là **hợp lý ở nghĩa hẹp**.

Nhưng cần tách hai khái niệm:

- **language purity:** đạt tương đối;
- **Korean editorial naturalness:** chưa được chứng minh.

Nhiều câu có tính chất dịch máy hoặc văn phong báo cáo chung chung, ví dụ:

> “대외적인 신뢰와 합법적 외관 이면에 숨겨진 실체와 의혹이 폭로되었습니다.”

và:

> “단기적인 이익 극대화 구조가 장기적인 시스템 붕괴를 가속화하는 구조적 모순이 발생했습니다.”

Các câu này không sai rõ ràng về ngữ pháp, nhưng nặng tính trừu tượng, lặp cấu trúc và thiếu chủ thể cụ thể. Chúng giống “forensic boilerplate” hơn là lời dẫn phóng sự Hàn Quốc tự nhiên.

**Đánh giá:** sạch ngôn ngữ ở mức lọc contamination; chưa đạt chuẩn biên tập bản ngữ.

---

## 2. Có cấu trúc Docudrama 5 Beat không?

Không. Script có thể được chia cơ học thành năm phần, nhưng đó không phải cấu trúc 5 Beat có chức năng.

### Beat 1 — Hook

Câu mở đầu:

> “급격한 시장 위기 속에서, 보증금의 덫: 전세사기 최소보장제와 한국형 그림자 금융의 붕괴 사태는 광범위한 구조적 충격을 촉발했습니다.”

Đây là một câu mở đầu lớn, trừu tượng và nhiều danh từ. Nó nêu “khủng hoảng”, “bẫy tiền đặt cọc”, “tín dụng bóng tối”, “cú sốc cấu trúc”, nhưng không có:

- nạn nhân;
- số tiền;
- mốc thời gian;
- câu hỏi cụ thể;
- tình huống nghịch lý.

Đây là **headline tổng quát**, không phải hook điều tra mạnh.

### Beat 2 — Setup

Các câu tiếp theo nói về:

- lỗ hổng;
- vẻ ngoài hợp pháp;
- hồ sơ;
- niềm tin thị trường;
- vận hành bề ngoài lành mạnh.

Nhưng không giới thiệu được:

- Jeonse hoạt động cụ thể ra sao;
- người thuê giao tiền như thế nào;
- rủi ro nằm ở chênh lệch tài sản và tiền đặt cọc nào;
- chính sách Minimum Guarantee Scheme là gì.

### Beat 3 — Escalation

Có các câu về:

- cảnh báo nội bộ;
- đòn bẩy;
- dữ liệu vận hành;
- thanh khoản biến mất.

Nhưng không có chuỗi nhân quả cụ thể. Không biết:

- ai làm gì;
- bằng công cụ nào;
- lỗ hổng nào cho phép hành vi đó;
- thiệt hại chuyển sang người thuê ra sao.

### Beat 4 — Reveal / confrontation

Script nói:

> “결정적 증거와 내부 고발이 이어지며 은폐되었던 거래 메커니즘이 완전히 해체되었습니다.”

Nhưng không đưa ra “bằng chứng quyết định” nào. Không có tài liệu, cuộc điều tra, cơ quan, giao dịch, chủ thể hay con số nào được tiết lộ.

Đây là **tuyên bố có reveal**, không phải reveal.

### Beat 5 — Resolution

Đoạn kết nói về:

- cơ quan quản lý;
- trách nhiệm pháp lý;
- cải cách;
- bài học về giám sát.

Nhưng không giải thích chính sách trung tâm:

- pre-application bắt đầu khi nào;
- có hiệu lực khi nào;
- ai đủ điều kiện;
- mức tối thiểu là bao nhiêu;
- đây là bảo lãnh toàn bộ hay chỉ ngưỡng tối thiểu;
- tác động và giới hạn của chính sách.

**Kết luận:** script có hình thức 5 đoạn, nhưng **không có 5 Beat theo nghĩa điều tra–kịch tính–nhân quả**.

---

## 3. Nhịp độ: 246 từ cho 240 giây

Tỷ lệ:

> 246 / 240 ≈ 1,03 đơn vị từ mỗi giây

không đủ để kết luận script có nhịp đọc đúng.

Đối với tiếng Hàn, dùng “word” theo khoảng trắng là thước đo kém tin cậy hơn so với:

- số ký tự Hangul;
- số âm tiết;
- số eojeol;
- tốc độ đọc thực tế của voice model;
- thời lượng pause;
- nhấn câu và khoảng ngắt.

246 đơn vị cách nhau trong 240 giây có thể cho cảm giác chậm vừa phải nếu có hình ảnh, pause và nhấn mạnh. Nhưng với 22 dòng văn bản trừu tượng, nó có nguy cơ tạo ra:

- khoảng trống dài;
- nhịp đều và phẳng;
- cảm giác kéo dài bằng pause thay vì bằng kịch tính;
- thời lượng “đủ gate” nhưng thiếu thông tin.

Quan trọng hơn, **word budget đang được dùng như proxy cho duration**, trong khi nội dung tiếng Hàn chưa được kiểm chứng bằng TTS hoặc benchmark speech-rate. Gate `duration_estimate_in_window = true` chỉ chứng minh phép tính của hệ thống hợp ngưỡng, không chứng minh audio thực tế đạt 240 giây với nhịp phóng sự tự nhiên.

**Đánh giá:** duration gate có thể đúng về số học, nhưng chưa đủ tin cậy về âm thanh thực.

---

## 4. Mức độ bám sát đề tài

Đây là lỗi nghiêm trọng nhất.

Đề tài là:

> chính sách bảo đảm tối thiểu tiền đặt cọc cho nạn nhân lừa đảo Jeonse tại Hàn Quốc.

Evidence Ledger có 8 claim cụ thể. Script thực tế gần như không dùng claim nào. Không thấy:

- MOLIT;
- ngày 10/11/2026;
- ngày 13/11/2026;
- mức 1/3;
- 9.317 nạn nhân tại Gyeonggi;
- HUG;
- “Villa Kings”;
- cơ chế proxy landlord;
- appraisal bị thổi phồng;
- tiền đặt cọc được tái đầu tư vào nhiều bất động sản;
- khác biệt giữa recovery và guarantee.

Thay vào đó, script nói các câu có thể áp dụng cho:

- bê bối ngân hàng;
- gian lận bảo hiểm;
- quỹ đầu tư;
- khủng hoảng bất động sản;
- công ty phá sản;
- rửa tiền.

Một kiểm thử đơn giản cho thấy thất bại:

> Nếu thay “전세사기” và “보증금” bằng “quỹ đầu tư sụp đổ”, phần lớn script vẫn có thể tồn tại mà không cần viết lại.

Đó là dấu hiệu **topic anchoring thất bại**.

---

## 5. Tính nhân quả

Các câu như:

> “시장 이해관계자들은 단기적인 성과를 앞세워 리스크를 은폐했습니다.”

và:

> “단기적인 이익 극대화 구조가 장기적인 시스템 붕괴를 가속화하는 구조적 모순이 발생했습니다.”

khẳng định quan hệ nhân quả nhưng không chỉ ra:

- actor;
- hành động;
- cơ chế;
- bằng chứng;
- kết quả định lượng.

Đối với một script forensic, đây là vấn đề lớn. Ngôn ngữ nhân quả không thể chỉ dựa trên các danh từ như “cấu trúc”, “rủi ro”, “sụp đổ”, “che giấu”. Mỗi causal beat phải trả lời:

1. Ai thực hiện?
2. Họ sử dụng cơ chế nào?
3. Cơ chế đó chuyển rủi ro sang ai?
4. Claim nào chứng minh điều này?
5. Hệ quả cụ thể là gì?

Script không trả lời các câu hỏi đó.

---

## 6. S04 gate có thực chất không?

Các gate hiện tại có giá trị, nhưng phạm vi rất hạn chế:

| Gate | Đánh giá |
|---|---|
| `duration_estimate_in_window` | Có giá trị số học; chưa chứng minh thời lượng TTS thực |
| `every_factual_line_has_claim_id` | Có giá trị nếu claim ID thật sự gắn với line; artifact không thể hiện điều đó |
| `legal_language_matches_status` | Cần thiết; chưa chứng minh mức độ bao phủ |
| `hook_within_20s` | Có thể đo vị trí; không đo chất lượng hook |
| `pattern_interrupt_gap_ok` | Đo nhịp cấu trúc; không đo sức nặng nội dung |
| `target_market_language_compliance` | Phát hiện contamination cơ bản; không đo tự nhiên và ngữ nghĩa |

Điểm yếu lớn nhất là bộ gate không có các kiểm tra sau:

1. **Claim coverage**  
   Có sử dụng các claim bắt buộc hoặc claim có priority cao không?

2. **Topic specificity**  
   Script có đủ thực thể, ngày, số liệu và cơ chế riêng của đề tài không?

3. **Evidence fidelity**  
   Câu văn có diễn giải đúng claim hay phóng đại claim?

4. **Causal graph completeness**  
   Các mũi tên nguyên nhân–hậu quả có được thể hiện không?

5. **Entity coverage**  
   Các chủ thể quan trọng như MOLIT, HUG, victim, landlord, appraisal agency có xuất hiện không?

6. **Genericity / substitution test**  
   Script có thể thay tên vụ việc bằng một vụ khác mà vẫn không thay đổi nội dung không?

7. **Unsupported assertion detection**  
   Các câu như “유동성이 증발했습니다” hoặc “자산 가치가 허구였음” có claim tương ứng không?

Do đó, S04 đã trở thành một **syntactic and structural validator**, chưa phải **forensic content validator**.

Điểm `9.4/10` vì vậy bị thổi phồng nếu được hiểu là chất lượng script tổng thể. Điểm đó chỉ có thể đại diện cho một số gate đã pass, không đại diện cho:

- độ bám đề tài;
- độ trung thực với evidence;
- chất lượng điều tra;
- giá trị sử dụng trong sản xuất.

---

# CÁC SỬA ĐỔI BẮT BUỘC TRƯỚC KHI VÀO S05

## 1. Buộc S03 sử dụng claim trọng yếu

Không được chỉ kiểm tra “mỗi factual line có claim ID”. Phải kiểm tra thêm:

- claim coverage tối thiểu;
- claim priority;
- claim bắt buộc theo story profile;
- lý do loại bỏ claim;
- không được pass nếu script không sử dụng các claim trọng yếu.

Với artifact này, tối thiểu cần xuất hiện có kiểm soát các nhóm:

- chính sách là gì;
- mốc hiệu lực;
- mức bảo đảm 1/3;
- đối tượng được chứng nhận;
- quy mô nạn nhân;
- cơ chế Jeonse;
- cơ chế gian lận;
- giới hạn hoặc điều kiện của chính sách.

## 2. Thêm `topic_specificity_gate`

Gate nên kiểm tra sự hiện diện có ngữ cảnh của:

- tên chương trình;
- thị trường;
- cơ quan;
- ngày;
- số liệu;
- nhân vật/chủ thể;
- cơ chế gây thiệt hại;
- kết quả hoặc phản ứng chính sách.

Không nên chỉ kiểm tra keyword đơn lẻ; cần kiểm tra chúng nằm trong câu có quan hệ ngữ nghĩa đúng.

## 3. Thêm genericity test

Sinh hoặc chạy một phép thử thay thế thực thể:

- thay `전세사기` bằng một scandal khác;
- thay `보증금` bằng `투자금`;
- thay `MOLIT` bằng một cơ quan khác.

Nếu phần lớn script vẫn hợp lệ mà không cần sửa, script phải bị reject vì quá generic.

## 4. Tách word budget khỏi audio duration

Cần benchmark theo:

- ký tự;
- âm tiết;
- eojeol;
- tốc độ TTS thực tế;
- pause budget;
- nhịp đọc theo market/language.

## 5. Mở rộng Language Gate

Cần bổ sung:

- foreign-script contamination;
- native-language classifier;
- terminology allowlist/denylist;
- native fluency review hoặc model-based linguistic scoring;
- kiểm tra tên riêng và thuật ngữ pháp lý;
- kiểm tra văn phong theo market.

## 6. Thêm semantic regression tests

Bộ test hiện tại đạt `5/5` nhưng chưa kiểm tra lỗi nghiêm trọng nhất: pipeline nhận grounding cụ thể nhưng sinh nội dung chung chung.

Cần có test kiểu:

> Input grounding thay đổi từ Jeonse sang một vụ việc khác thì output phải thay đổi ở các thực thể, cơ chế, số liệu và causal beats tương ứng.

---

# VERDICT CUỐI CÙNG

## **CHƯA ĐẠT — REVISE**

Lý do không phải vì còn vài từ tiếng Anh hay một lỗi format. Lý do là:

1. **Code đã có nhiều sửa chữa mang tính hệ thống ở tầng plumbing và orchestration.**
2. **DAG invalidation hiện cho thấy kết quả vận hành tốt trong run này.**
3. **Language gate đã loại được contamination bề mặt.**
4. Nhưng **S03 không chuyển evidence cụ thể thành một câu chuyện cụ thể**.
5. Script **không có 5 Beat điều tra thực chất**.
6. Script **quá generic, thiếu claim, thiếu chủ thể, thiếu mốc thời gian, thiếu số liệu và thiếu causal mechanism**.
7. S04 **pass các điều kiện hình thức nhưng bỏ lọt lỗi semantic nghiêm trọng**.
8. Điểm `9.4/10` không phản ánh chất lượng forensic thực tế của artifact.

**Không được chuyển sang S05.** Nếu chuyển tiếp, Director Plan sẽ chỉ tạo hình ảnh và blocking cho một kịch bản rỗng bằng chứng, từ đó nhân bản lỗi xuống toàn bộ S05–S11.