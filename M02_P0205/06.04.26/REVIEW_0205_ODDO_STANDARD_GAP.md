# Đánh Giá Module 0205 So Với Giải Pháp Chuẩn Của Odoo

Tài liệu này tổng hợp các điểm trong module `M02_P0205` có dấu hiệu:

- làm lại chức năng mà Odoo hoặc addon chuẩn của Odoo đã có sẵn
- xử lý theo hướng custom riêng, trong khi Odoo đã có pattern chuẩn để giải quyết

Mục tiêu của tài liệu là giúp đánh giá xem phần nào nên giữ nguyên vì phù hợp nghiệp vụ riêng, và phần nào nên cân nhắc refactor để bám chuẩn Odoo hơn.

## 1. Các điểm có dấu hiệu làm lại giải pháp chuẩn của Odoo

### 1.1. `recruitment.request` đang tự dựng lại quy trình phê duyệt mà Odoo đã có `approvals`

- File custom: `addons/M02_P0205/models/recruitment_request.py`
- Model custom: `recruitment.request`
- Dấu hiệu:
  - tự tạo model riêng để làm yêu cầu tuyển dụng
  - tự quản lý `approver_ids`
  - tự quản lý `state`
  - tự viết các bước `action_submit`, `action_hr_validate`, `action_ceo_approve`
  - tự tạo và điều phối `mail.activity`

Trong khi đó, addon chuẩn `approvals` của Odoo đã có sẵn:

- model `approval.request`
- danh sách người duyệt `approver_ids`
- trạng thái phê duyệt `request_status`
- các hàm chuẩn như `action_confirm`, `action_approve`
- cơ chế duyệt tuần tự / song song
- cơ chế tự tạo activity cho approver

Nhận định:

- Đây là điểm rõ nhất cho thấy module `0205` đang làm lại một giải pháp chuẩn của Odoo.
- Vì `0205` đã phụ thuộc trực tiếp vào `approvals`, nên về mặt kiến trúc, đáng lẽ có thể tận dụng `approval.request` hoặc một lớp mở rộng tương tự thay vì dựng một engine duyệt riêng.

Rủi ro:

- logic phê duyệt bị phân tán
- khó tận dụng UI, quyền, activity, report, lịch sử phê duyệt sẵn có của `approvals`
- về sau khó đồng bộ với các module khác trong hệ thống đang dùng chuẩn `approvals`

## 1.2. Phần gửi và theo dõi khảo sát trên `hr.applicant` đang làm lại nhiều phần mà `hr_recruitment_survey` đã có

- File custom: `addons/M02_P0205/models/hr_applicant.py`
- Các field custom liên quan:
  - `survey_sent`
  - `survey_result_url`
- Hàm custom liên quan:
  - `action_send_survey`
  - `_handle_office_pre_interview_survey_done`
  - `action_view_survey_result`

Trong khi đó, addon chuẩn `hr_recruitment_survey` của Odoo đã có sẵn:

- `job.survey_id`
- `applicant.survey_id`
- `response_ids`
- wizard chuẩn để gửi khảo sát cho ứng viên
- luồng liên kết `survey.user_input` với `hr.applicant`

Nhận định:

- Phần gửi mail khảo sát, gắn khảo sát với ứng viên, mở wizard khảo sát, theo dõi response là những phần Odoo đã có solution chuẩn.
- Module `0205` đang tự viết lại đáng kể phần này.
- Tuy nhiên, đoạn xử lý nghiệp vụ riêng như:
  - kiểm tra câu hỏi bắt buộc
  - đưa ứng viên sang `Screening`
  - tạo follow-up activity sau khi làm khảo sát

  thì đây là custom hợp lý, vì đó là logic đặc thù nghiệp vụ văn phòng của bạn.

Rủi ro:

- chồng chéo logic giữa custom và `hr_recruitment_survey`
- khó bảo trì khi Odoo nâng cấp flow survey chuẩn
- có thể xuất hiện hai cách gửi survey song song trong cùng hệ thống

## 1.3. `survey_id` trên `hr.job` đang bị khai báo lại dù addon chuẩn đã có

- File custom: `addons/M02_P0205/models/hr_job.py`
- Field custom: `survey_id`

Trong khi đó, addon chuẩn `hr_recruitment_survey` đã có sẵn field `survey_id` trên `hr.job`.

Nhận định:

- Nếu mục tiêu của `0205` chỉ là giới hạn domain hoặc gắn nhãn “pre-interview”, thì cách an toàn hơn thường là:
  - kế thừa field có sẵn
  - điều chỉnh view
  - hoặc thêm ràng buộc/domain ở lớp phù hợp

- Việc khai báo lại field vốn đã có trong addon chuẩn là dấu hiệu “làm lại” không cần thiết.

Rủi ro:

- dễ phát sinh xung đột với addon chuẩn
- khó đoán field nào là nguồn sự thật chính
- có nguy cơ lệch hành vi giữa các module phụ thuộc `survey_id`

## 1.4. Một số field chuẩn của `hr.applicant` đang bị làm lại ý nghĩa thay vì tận dụng cấu trúc sẵn có của Odoo

- File custom: `addons/M02_P0205/models/hr_applicant.py`

Các ví dụ:

- redefine `stage_id`
- redefine `priority`
- thêm các field cố định theo từng vòng:
  - `interview_date_1` đến `interview_date_4`
  - `interview_result_1` đến `interview_result_4`
  - `primary_interviewer_l1_user_id` đến `primary_interviewer_l4_user_id`
  - `eval_round_1_score` đến `eval_round_4_score`
  - `eval_round_1_pass` đến `eval_round_4_pass`

Trong khi `hr_recruitment` chuẩn đã có rất nhiều field và pattern sẵn:

- `stage_id`
- `priority`
- `meeting_ids`
- `interviewer_ids`
- `refuse_reason_id`
- `salary_expected`
- `availability`
- `source_id`
- `medium_id`

Nhận định:

- Phần bài toán đánh giá nhiều vòng là nghiệp vụ riêng, nên việc custom là hợp lý.
- Tuy nhiên, cách biểu diễn dữ liệu theo kiểu “field cố định cho từng vòng” là hướng khá đóng cứng.
- Odoo thường thiên về pattern One2many / line model cho dữ liệu lặp theo vòng hoặc theo bước.

Điều này có nghĩa:

- không phải là làm lại hoàn toàn giải pháp có sẵn của Odoo
- nhưng là đang chọn cách custom cứng hơn so với pattern dữ liệu chuẩn mà Odoo thường dùng

Rủi ro:

- khó mở rộng nếu sau này số vòng thay đổi
- code/view/report dễ phình to
- logic compute và cảnh báo sẽ ngày càng phức tạp hơn

## 1.5. `action_go_to_portal_home()` đang tự tạo blog post tuyển dụng, trong khi `website_hr_recruitment` đã có job page chuẩn

- File custom: `addons/M02_P0205/models/hr_job.py`
- Hàm custom: `action_go_to_portal_home`

Trong hàm này, module:

- publish job
- tự tìm hoặc tạo `blog.blog`
- tự tạo `blog.post`
- tự build nội dung HTML để đăng tin tuyển dụng

Trong khi đó, addon chuẩn `website_hr_recruitment` đã có:

- `website_published`
- `website_url`
- `website_description`
- `full_url`
- trang tuyển dụng chuẩn dạng `/jobs/...`

Nhận định:

- Nếu mục tiêu là đăng tuyển công khai trên website tuyển dụng của Odoo, thì Odoo đã có sẵn luồng chuẩn.
- Việc dùng blog để đăng tin tuyển dụng có thể phù hợp nếu bạn muốn thêm một kênh truyền thông/phổ biến nội dung.
- Nhưng nếu blog được dùng như luồng chính để thay thế job page chuẩn, thì đây là một dạng đi vòng và làm mới giải pháp mà Odoo đã cung cấp.

Rủi ro:

- dữ liệu tuyển dụng bị tách làm hai nơi: job page và blog
- khó đồng bộ nội dung
- khó quản trị SEO, cập nhật trạng thái hoặc đóng tuyển thống nhất

## 2. Những phần custom mình đánh giá là hợp lý

Không phải phần custom nào cũng là “làm lại vô ích”. Có những phần trong `0205` là custom hợp lý vì nghiệp vụ riêng của doanh nghiệp không có sẵn trong Odoo chuẩn.

### 2.1. `hr.applicant.evaluation`

- Model:
  - `hr.applicant.evaluation`
  - `hr.applicant.evaluation.line`

Nhận định:

- Odoo chuẩn không có sẵn đúng cấu trúc phiếu đánh giá phỏng vấn nhiều vòng như module này.
- Đây là phần custom hợp lý và có giá trị nghiệp vụ rõ ràng.

### 2.2. `recruitment.plan` và `recruitment.batch`

- Model:
  - `recruitment.plan`
  - `recruitment.plan.line`
  - `recruitment.batch`

Nhận định:

- Đây có vẻ là lớp nghiệp vụ riêng của doanh nghiệp để quản lý kế hoạch tổng, kế hoạch con và đợt tuyển dụng.
- Odoo core không có sẵn mô hình tương ứng ở mức đúng như vậy.
- Vì vậy đây không phải là dấu hiệu “làm lại nguyên xi” chức năng chuẩn.

## 3. Kết luận tổng thể

Có, module `0205` hiện đang có một số phần mang tính:

- tự làm lại chức năng mà Odoo đã có sẵn
- hoặc đi theo hướng custom riêng trong khi Odoo đã có pattern chuẩn rõ ràng

Ba khu vực đáng chú ý nhất là:

- quy trình phê duyệt yêu cầu tuyển dụng
- quy trình gửi và theo dõi khảo sát tuyển dụng
- cơ chế publish tin tuyển dụng ra website/blog

Trong đó:

- phần `approval` là chỗ trùng lặp rõ nhất với giải pháp chuẩn Odoo
- phần `survey recruitment` là chỗ chồng chéo tương đối rõ với addon chuẩn
- phần `blog tuyển dụng` là một hướng xử lý riêng, nhưng dễ đi lệch khỏi flow chuẩn của `website_hr_recruitment`

## 4. Khuyến nghị

### Nên cân nhắc refactor

- `recruitment.request` theo hướng tận dụng `approval.request` hoặc một abstraction approval dùng chung trong hệ thống
- flow survey theo hướng mở rộng `hr_recruitment_survey` thay vì viết lại lớp gửi/track cơ bản
- hạn chế redefine các field chuẩn đã tồn tại như `survey_id`

### Có thể giữ nguyên

- mô hình đánh giá phỏng vấn nhiều vòng
- mô hình kế hoạch tuyển dụng / đợt tuyển dụng
- các rule nghiệp vụ riêng của khối văn phòng

### Nên theo dõi thêm

- các field cố định theo từng vòng phỏng vấn trên `hr.applicant`
- logic tạo activity thủ công
- các chỗ publish dữ liệu ra nhiều kênh khác nhau

Nếu về sau muốn làm sạch kiến trúc, nên ưu tiên chuẩn hóa theo thứ tự:

1. chuẩn hóa approval
2. chuẩn hóa survey recruitment
3. chuẩn hóa publish website tuyển dụng

