# Plan: Đồng bộ phiếu đánh giá phỏng vấn Odoo theo file Excel khách hàng

## Mục tiêu

Điều chỉnh phiếu đánh giá phỏng vấn trong `0205` để bám sát mẫu Excel khách hàng:

- file tham chiếu: `addons/M02_P0205/notes/RST_Interview Evaluation Form - 24.03.2026.xlsx`
- sheet chính: `Interview Evaluation Form`

Mục tiêu không chỉ là sửa giao diện, mà phải đồng bộ cả:

- cấu trúc dữ liệu lưu đánh giá
- form nhập đánh giá trong Odoo
- cách tổng hợp điểm / kết quả cuối

## Hiện trạng Odoo

Phiếu đánh giá hiện tại trong `0205` đang là form khá gọn, gồm:

- thông tin chung:
  - interviewer
  - primary interviewer
  - is primary interviewer
  - date
  - recommendation
- 4 tiêu chí điểm 1-5:
  - `attitude_score`
  - `skill_score`
  - `experience_score`
  - `culture_fit_score`
- text:
  - `strengths`
  - `weaknesses`
  - `note`

Nói ngắn:

- Odoo hiện đang dùng cấu trúc cố định 4 tiêu chí
- form hiện tại chưa phản ánh bố cục nhiều section như mẫu Excel

## Hiện trạng file Excel khách hàng

Theo file Excel hiện tại, phiếu đánh giá có các phần chính:

### 1. Header thông tin

- Candidate Name
- Position
- Interview Date
- Interviewer

### Ý nghĩa và vai trò

- đây là phần định danh của phiếu đánh giá
- giúp biết:
  - phiếu này thuộc ứng viên nào
  - đánh giá cho vị trí nào
  - ai là người đánh giá
  - đánh giá vào thời điểm nào
- vai trò chính:
  - phục vụ truy vết
  - làm cơ sở đối chiếu giữa các vòng / các interviewer
  - là phần header bắt buộc nếu sau này cần in hoặc export lại phiếu

### 2. Thang đo 1-5

Có legend theo mức độ:

- mức thấp: inexperience / low expertise
- mức trung bình: experience nhưng chưa lead/train
- mức cao: expertise + leading mindset

### Ý nghĩa và vai trò

- đây là rubric chấm điểm chung cho toàn bộ phiếu
- mục tiêu là chuẩn hóa cách hiểu giữa các interviewer khi chọn điểm 1-5
- vai trò chính:
  - giảm tình trạng mỗi người hiểu điểm 3/4/5 khác nhau
  - giúp người chấm có cùng chuẩn khi đánh giá nhiều ứng viên
  - tạo nền cho việc tổng hợp điểm cuối có ý nghĩa nhất quán

### 3. Section `FUNCTIONAL SKILLS`

Gồm:

- `Candidate Fit scale`
  - có 3 key points
- `Skillset mapping`
  - Technical / Hard skills
  - Role-specific skills
  - Soft skills
- mỗi nhóm có:
  - điểm 1-5
  - note hỗ trợ cho lựa chọn

### Ý nghĩa và vai trò

- đây là phần đánh giá năng lực làm việc trực tiếp liên quan đến job
- thường trả lời câu hỏi:
  - ứng viên có phù hợp với yêu cầu công việc thực tế hay không
  - kỹ năng nền và kỹ năng đặc thù có đủ để làm việc không
- các nhóm bên trong có vai trò riêng:
  - `Candidate Fit scale`
    - ghi lại 3 điểm then chốt để giải thích mức độ phù hợp tổng quan của ứng viên
    - giống phần snapshot nhanh cho interviewer
  - `Technical/Hard skills`
    - đánh giá năng lực công cụ, kỹ thuật, kiến thức thực hành
  - `Role-specific skills`
    - đánh giá mức độ phù hợp với yêu cầu riêng của vị trí đang tuyển
  - `Soft skills`
    - đánh giá khả năng phối hợp, giao tiếp, xử lý vấn đề
- cột note trong section này rất quan trọng vì:
  - không chỉ chấm điểm
  - mà còn yêu cầu người phỏng vấn nêu căn cứ cho điểm đã chọn

### 4. Section `BEST LEADERSHIP`

Các mục đang thấy trong file:

- Background & Values (Culture Fit)
- Building Block
- Execution
- Strategy
- Talent
- Brand Love

### Ý nghĩa và vai trò

- đây là phần đánh giá theo khung năng lực hành vi / leadership mindset
- không thuần là kỹ năng làm việc, mà là mức độ phù hợp với cách làm việc và định hướng lãnh đạo của tổ chức
- vai trò của các nhóm:
  - `Background & Values (Culture Fit)`
    - đo độ phù hợp văn hóa và giá trị nền
  - `Building Block`
    - xem ứng viên có nền tảng tốt để phát triển tiếp không
  - `Execution`
    - đo năng lực triển khai và theo việc đến cùng
  - `Strategy`
    - đo tư duy định hướng, nhìn bài toán ở mức rộng hơn
  - `Talent`
    - xem tiềm năng phát triển / mức độ nổi bật của ứng viên
  - `Brand Love`
    - phản ánh mức độ gắn kết, hiểu và yêu thích thương hiệu / môi trường công ty
- section này có vai trò phân biệt:
  - ứng viên “làm được việc”
  - với ứng viên “phù hợp để đi đường dài”

### 5. Section `CHARACTER TRAITS`

- Trait #1
- Trait #2
- Trait #3

### Ý nghĩa và vai trò

- đây là phần ghi nhận các đặc điểm tính cách hoặc dấu ấn hành vi nổi bật
- khác với phần leadership ở chỗ:
  - leadership là khung đánh giá theo năng lực hành vi
  - character traits là ghi nhận nhận xét cô đọng về con người ứng viên
- vai trò chính:
  - giúp lưu lại nhận định định tính
  - hỗ trợ khi so sánh giữa nhiều ứng viên cùng vị trí
  - có thể dùng làm căn cứ để onboarding hoặc bố trí quản lý sau này

### 6. Tổng hợp cuối

- Overall
- Score
- Final Result
- Onboard Time
- câu hỏi recommendation:
  - `Do you recommend we move forward with this candidate?`

### Ý nghĩa và vai trò

- đây là phần chốt kết quả cuối của phiếu đánh giá
- vai trò từng mục:
  - `Overall`
    - vùng tổng hợp nhìn nhanh toàn bộ kết quả
  - `Score`
    - điểm số cuối để hỗ trợ so sánh tương đối
  - `Final Result`
    - kết luận chính thức của phiếu
  - `Onboard Time`
    - ghi nhận khả năng hoặc thời điểm có thể onboard
  - `Do you recommend we move forward with this candidate?`
    - câu hỏi quyết định mang tính nghiệp vụ tuyển dụng
    - là cầu nối giữa đánh giá phỏng vấn và quyết định đi tiếp / dừng

### Ý nghĩa tổng thể của phần cuối

- nếu các section phía trên là dữ liệu đầu vào
- thì phần này là lớp quyết định đầu ra
- đây là phần quan trọng nhất để map về logic Odoo hiện tại như:
  - `recommendation`
  - `pass/fail`
  - stage flow của applicant

## Công thức đánh giá theo file Excel

Theo các công thức đang có trong file Excel, logic chấm điểm hiện tại là:

### 1. Đếm số dấu `x` theo từng cột điểm

Các cột điểm từ 1 đến 5 tương ứng với các cột:

- cột `1` -> `C`
- cột `2` -> `D`
- cột `3` -> `E`
- cột `4` -> `F`
- cột `5` -> `G`

Vùng chấm điểm đang được dùng trong công thức là:

- `C11:G32`

### 2. Overall theo từng mức điểm

Excel đang tính tổng điểm quy đổi theo từng cột như sau:

- `C33 = COUNTIF(C11:C28,"x") * 1`
- `D33 = COUNTIF(D11:D28,"x") * 2`
- `E33 = COUNTIF(E11:E28,"x") * 3`
- `F33 = COUNTIF(F11:F28,"x") * 4`
- `G33 = COUNTIF(G11:G28,"x") * 5`

### Ý nghĩa

- đếm xem có bao nhiêu tiêu chí được tick ở mức 1, 2, 3, 4, 5
- sau đó nhân với trọng số tương ứng của mức điểm
- hàng `OVERALL` thực chất là tổng điểm đã quy đổi theo từng mức 1-5

### 3. Tổng số tiêu chí đã được chấm

Excel đang tính:

- `H33 = COUNTIF(C11:G32,"x")`

### Ý nghĩa

- đây là tổng số ô đã được tick
- cũng chính là số lượng tiêu chí thực tế đã được chấm điểm
- giá trị này được dùng làm mẫu số để tính điểm trung bình

### 4. Điểm trung bình cuối (`Score`)

Excel đang tính:

- `C34 = SUM(C33:G33) / H33`

### Ý nghĩa

- `Score` là điểm trung bình cộng có trọng số của toàn bộ tiêu chí đã chấm
- tương đương:
  - tổng điểm quy đổi của tất cả tiêu chí
  - chia cho số tiêu chí đã được đánh giá

### 5. Kết quả cuối (`Final Result`)

Excel đang tính:

- `C35 = IF(C34 >= 3, "Pass", "Reject")`

### Ý nghĩa

- ngưỡng pass của phiếu Excel hiện tại là:
  - `Score >= 3`
- nếu dưới 3:
  - kết quả là `Reject`

## Diễn giải nghiệp vụ từ công thức Excel

Từ công thức trên, có thể rút ra logic nghiệp vụ như sau:

- mỗi tiêu chí hiện đang có trọng số ngang nhau
- không có trọng số riêng cho từng section
- `Final Result` hiện tại được derive tự động từ `Score`
- `Score` đóng vai trò rất trung tâm trong việc quyết định pass / reject

## Tác động tới thiết kế Odoo

### 1. Mỗi dòng tiêu chí phải lưu được điểm 1-5

Vì công thức Excel tính theo từng ô tick trên từng dòng, nên Odoo cần lưu được:

- từng tiêu chí
- điểm 1-5 của tiêu chí đó

### 2. Header evaluation cần có field tổng hợp

Khuyến nghị thêm hoặc tính ra các field:

- `scored_line_count`
- `weighted_total_score`
- `average_score`
- `final_result`

### 3. Cần tách rõ `final_result` và `recommendation`

File Excel đang dùng:

- `Final Result = Pass/Reject`

Trong khi Odoo hiện có:

- `recommendation = pass/fail`

Khuyến nghị:

- ngắn hạn có thể map trực tiếp:
  - `Pass` -> `pass`
  - `Reject` -> `fail`
- nhưng trong thiết kế nên tách ý nghĩa:
  - `final_result` là kết quả tính theo score
  - `recommendation` là kết luận nghiệp vụ cuối cùng

Lý do:

- về sau business có thể muốn interviewer override kết quả tự động theo score
- hoặc muốn giữ đồng thời:
  - điểm số khách quan
  - kết luận chủ quan của interviewer

## Nhận định khoảng cách giữa Excel và Odoo

### 1. Khác biệt lớn nhất

Excel không còn là form 4 tiêu chí cố định nữa.

Nó đang gần với mô hình:

- nhiều section
- nhiều dòng tiêu chí
- có cột điểm 1-5
- có notes cho từng mục
- có tổng hợp cuối

### 2. Form hiện tại của Odoo không đủ dữ liệu

Nếu chỉ sửa UI mà vẫn giữ model cũ:

- không lưu được đầy đủ từng dòng đánh giá
- không tái hiện được structure của file Excel
- không tổng hợp được đúng kiểu khách hàng mong muốn

### 3. Cần xác định mức độ “giống Excel”

Trước khi code, phải chốt rõ:

- chỉ cần UI gần giống Excel
- hay phải lưu đúng từng dòng dữ liệu như Excel
- hay còn cần export / print ra đúng form Excel

Khuyến nghị:

- giai đoạn đầu nên tập trung:
  - lưu đúng dữ liệu
  - nhập liệu đúng structure
- export/print giống hệt Excel có thể là phase sau

## Định hướng triển khai

## Phase 1. Chốt mapping nghiệp vụ từ Excel sang dữ liệu Odoo

### Mục tiêu

Xác định phần nào của Excel sẽ thành field cố định, phần nào sẽ thành line động.

### Cần chốt

1. `Final Result`
- vẫn giữ kiểu `pass/fail`
- hay cần thêm kết quả khác

2. `Onboard Time`
- là text tự do
- hay date / period / available_from

3. `Candidate Fit scale`
- là 3 dòng text độc lập
- hay 1 nhóm line có score + note

4. `Character Traits`
- là text thuần
- hay cũng có score

### Khuyến nghị

- dùng model line động cho các tiêu chí đánh giá
- không tiếp tục hard-code 4 field score riêng lẻ

## Phase 2. Thiết kế lại data model

### Mục tiêu

Chuẩn hóa model để chứa được structure dạng section + line item.

### Hướng đề xuất

Giữ `hr.applicant.evaluation` làm header, và thêm model line chi tiết, ví dụ:

- `hr.applicant.evaluation.line`

Line có thể gồm:

- section
- item_code
- item_label
- score_1_5
- note
- sequence

### Header của evaluation giữ các field tổng quát

- applicant
- interview_round
- interviewer
- date
- recommendation
- final_score
- onboard_time
- final_comment

### Lợi ích

- bám được structure Excel
- dễ thêm/bớt tiêu chí sau này
- không phải sửa model mỗi lần khách đổi form

## Phase 3. Tạo bộ template tiêu chí mặc định

### Mục tiêu

Khi tạo evaluation mới, hệ thống tự sinh sẵn các dòng theo mẫu Excel.

### Hướng triển khai

Tạo sẵn template line theo nhóm:

- Functional Skills
- Best Leadership
- Character Traits

Ví dụ:

- Candidate Fit Point 1
- Candidate Fit Point 2
- Candidate Fit Point 3
- Technical Skill 1
- Technical Skill 2
- Role-specific Skill 1
- Role-specific Skill 2
- Soft Skill 1
- Soft Skill 2
- Background & Values
- Building Block
- Execution
- Strategy
- Talent
- Brand Love
- Trait 1
- Trait 2
- Trait 3

### Cần chốt thêm

- các label trên có cố định cho mọi job không
- hay sẽ khác theo nhóm vị trí

Khuyến nghị trước mắt:

- dùng 1 template chung giống file Excel khách hàng

## Phase 4. Sửa form view evaluation

### Mục tiêu

Đổi popup đánh giá hiện tại sang layout gần với mẫu Excel.

### File chính

- `addons/M02_P0205/views/hr_applicant_views.xml`

### Việc cần làm

- giữ khối thông tin chung
- thay 4 field điểm cũ bằng bảng/one2many line
- hiển thị theo từng section
- mỗi line có:
  - label tiêu chí
  - score 1-5
  - note
- thêm phần tổng hợp cuối:
  - score
  - final result
  - onboard time
  - recommendation

## Phase 5. Tính toán và tổng hợp kết quả

### Mục tiêu

Làm rõ cách tính `Score`, `Overall`, `Final Result`.

### Cần chốt nghiệp vụ

1. `Score`
- là trung bình các line
- hay có trọng số theo section

2. `Final Result`
- manual bởi interviewer
- hay derive tự động từ score

3. `Overall`
- là field hiển thị tổng điểm
- hay chỉ là summary section trong form

### Khuyến nghị

- giai đoạn đầu:
  - score tổng = trung bình line có điểm
  - final result vẫn để interviewer chốt manual

Lý do:

- an toàn hơn
- không thay đổi logic pass/fail hiện đang bám theo kết luận người phỏng vấn chính

## Phase 6. Migration dữ liệu cũ

### Mục tiêu

Xử lý các evaluation đã tồn tại trước khi đổi model.

### Hướng khả thi

1. Giữ lại field cũ song song một thời gian
- tạo line mặc định từ dữ liệu cũ nếu cần

2. Không migrate chi tiết
- chỉ áp dụng form mới cho evaluation phát sinh sau khi deploy

### Khuyến nghị

- nếu số dữ liệu cũ ít:
  - có thể không migrate chi tiết
- nếu cần continuity:
  - map 4 field cũ sang 4 line chuẩn trong section mới

## Phase 7. Đồng bộ tab tổng hợp trên applicant

### Mục tiêu

Đảm bảo các tab `PV Vòng 1..4` và phần `Đánh Giá (Evaluation)` vẫn đọc được dữ liệu mới.

### Việc cần làm

- rà các field đang hiển thị:
  - `eval_round_n_score`
  - `eval_round_n_toggle`
  - `eval_l1_id..eval_l4_id`
- cập nhật phần summary để không phụ thuộc 4 field score cũ

## Phase 8. Test end-to-end

### Case chính

1. Tạo evaluation mới
- line template phải tự sinh đủ theo Excel

2. Nhập điểm từng line
- score tổng phải cập nhật đúng

3. Save evaluation
- kết luận vòng vẫn cập nhật đúng flow applicant

4. Primary interviewer pass/fail
- logic round outcome không bị vỡ

5. Mở lại evaluation cũ
- không lỗi form

## Khuyến nghị triển khai thực tế

Nên chia làm 2 đợt:

### Đợt 1

- chốt mapping nghiệp vụ
- refactor model sang header + line
- dựng form mới gần với Excel
- giữ logic round outcome cũ

### Đợt 2

- tinh chỉnh UI giống Excel hơn
- tính toán summary nâng cao
- cân nhắc export / print đúng mẫu khách hàng

## Kết luận

Thay đổi này là refactor tương đối lớn, vì mẫu Excel khách hàng không còn phù hợp với cấu trúc 4 tiêu chí cố định hiện tại.

Hướng phù hợp nhất là:

- không chỉ sửa view
- mà chuyển sang model đánh giá dạng `header + dynamic lines`

Như vậy mới đủ linh hoạt để bám phiếu khách hàng hiện tại và tránh phải sửa model cứng thêm nhiều lần sau này.
