# Đánh Giá Nội Dung Đề Xuất Về Việc Giữ Hoặc Bỏ Model Trong `M02_P0204_00` Và `M02_P0205_00`

Tài liệu này ghi lại phần đánh giá đối với nội dung đề xuất về việc:

- model nào nên giữ
- model nào nên bỏ
- model nào nên gộp
- module nào nên là owner sau khi chuẩn hóa kiến trúc giữa `M02_P0204_00` và `M02_P0205_00`

## 1. Nhận định tổng quát

Nội dung đề xuất này đúng hướng về mặt kiến trúc, đặc biệt ở ý tưởng:

- `0204_00` nên là module base/shared
- `0205` chỉ nên mở rộng flow riêng cho office
- tránh để cả `0204_00` và `0205` cùng “sở hữu” những model chung

Đây là hướng hợp lý vì:

- `0205` đang phụ thuộc trực tiếp vào `0204_00`
- nếu cả hai cùng giữ owner trên các model shared, hệ thống sẽ tiếp tục khó kiểm soát
- việc chuẩn hóa owner sẽ giúp giảm chồng chéo field, model và logic

Tuy nhiên, nội dung hiện tại vẫn cần chỉnh lại một số điểm để kết luận được chặt hơn.

## 2. Những điểm phù hợp

### 2.1. `0204_00` làm base/shared, `0205` chỉ thêm office flow là hợp lý

Đây là hướng đúng nhất trong toàn bộ đề xuất.

`0204_00` hiện đang chứa khá nhiều phần mang tính nền tảng hoặc dùng chung cho tuyển dụng:

- stage typing
- survey dispatcher
- cấu hình job/survey
- store scheduling
- template và email rule

Trong khi đó, `0205` nên tập trung vào:

- office-specific flow
- recruitment plan / batch
- logic phỏng vấn nhiều vòng cho office
- các mở rộng riêng cho khối văn phòng

### 2.2. `is_pre_interview` nên chỉ có một owner duy nhất

Điểm này là đúng.

Hiện field `is_pre_interview` đang bị khai báo chồng giữa:

- `M02_P0204_00`: [survey_survey.py](d:\odoo-19.0+e.20250918\addons\M02_P0204_00\models\survey_survey.py#L11)
- `M02_P0205_00`: [survey_ext.py](d:\odoo-19.0+e.20250918\addons\M02_P0205_00\models\survey_ext.py#L5)

Với kiểu field shared như vậy, chỉ nên có một owner duy nhất. Để trong `0204_00` là hợp lý hơn vì `0204_00` đang đóng vai trò base/shared.

### 2.3. `survey_id` trên `hr.job` không nên redeclare ở `0205`

Điểm này cũng đúng.

Hiện `0205` đang khai báo lại `survey_id` ở:

- [hr_job.py](d:\odoo-19.0+e.20250918\addons\M02_P0205_00\models\hr_job.py#L33)

Trong khi addon chuẩn `hr_recruitment_survey` đã có sẵn field này ở:

- [hr_job.py](d:\odoo-19.0+e.20250918\odoo\addons\hr_recruitment_survey\models\hr_job.py#L9)

Nếu chỉ cần giới hạn domain hoặc thay đổi cách hiển thị, nên kế thừa field chuẩn thay vì khai báo lại.

### 2.4. Bộ model form động trong `0204` nên được xem xét gộp về property chuẩn của Odoo

Điểm này mình đồng ý khá mạnh.

Các model:

- `job.application.field`
- `recruitment.application.field.master`
- `hr.applicant.application.answer.line`

đang tạo thêm một lớp trung gian để quản lý form động.

Trong khi đó, Odoo core đã có:

- `applicant_properties_definition` trên `hr.job`
- `applicant_properties` trên `hr.applicant`

Các tham chiếu tương ứng:

- [hr_job.py](d:\odoo-19.0+e.20250918\odoo\addons\hr_recruitment\models\hr_job.py#L79)
- [hr_applicant.py](d:\odoo-19.0+e.20250918\odoo\addons\hr_recruitment\models\hr_applicant.py#L136)

Đặc biệt, chính `0204_00` cũng đang bridge sang property chuẩn ở:

- [job_application_field.py](d:\odoo-19.0+e.20250918\addons\M02_P0204_00\models\job_application_field.py#L317)

Vì vậy nhận định “nên gộp hẳn về property chuẩn, bỏ lớp model trung gian” là hợp lý.

### 2.5. Nên giữ `interview.schedule`, `recruitment.plan*`, `recruitment.batch`, `hr.applicant.oje.evaluation*`

Điểm này phù hợp.

Các model này đều là nghiệp vụ riêng, không thấy Odoo core có model tương ứng đủ gần để thay thế trực tiếp:

- `interview.schedule`
- `recruitment.plan`
- `recruitment.plan.line`
- `recruitment.batch`
- `hr.applicant.oje.evaluation`
- `hr.applicant.oje.evaluation.line`

Đây là những model có lý do tồn tại rõ ràng và có thể giữ lại sau chuẩn hóa.

## 3. Những điểm cần chỉnh lại

### 3.1. Đề xuất hiện tại đang bỏ sót một model approval trùng chuẩn ở `0204`

Nội dung hiện tại nói đúng về việc:

- `recruitment.request.approver` là model thừa
- `recruitment.request` đang làm lại một phần logic của `approval.request`

Nhưng chưa nhắc tới:

- `job.approval.request` của `0204`

Model này nằm tại:

- [job_approval_request.py](d:\odoo-19.0+e.20250918\addons\M02_P0204_00\models\job_approval_request.py#L5)

Và thực tế nó cũng đang tự dựng:

- `state`
- `approver_user_id`
- schedule activity
- approve / reject logic riêng

Các phần này xuất hiện ở:

- [job_approval_request.py](d:\odoo-19.0+e.20250918\addons\M02_P0204_00\models\job_approval_request.py#L32)
- [job_approval_request.py](d:\odoo-19.0+e.20250918\addons\M02_P0204_00\models\job_approval_request.py#L126)

Vì vậy, nếu kết luận là nên bỏ approval model riêng để về chuẩn Odoo, thì kết luận này phải áp dụng cho cả:

- `job.approval.request` của `0204`
- `recruitment.request.approver` của `0205`
- `recruitment.request` của `0205`

Không nên chỉ nhắm vào `0205`.

### 3.2. Câu “`0205` sở hữu `recruitment.request`” chưa thật nhất quán với phần refactor sang `approval.request`

Trong nội dung đề xuất có hai ý song song:

- `0205` sở hữu `recruitment.request`
- nên refactor header approval sang `approval.request`

Hai ý này dễ gây hiểu nhầm nếu giữ nguyên cách viết.

Nếu đã đi theo hướng chuẩn hóa mạnh, thì nên diễn đạt rõ hơn:

- `0205` sở hữu nghiệp vụ “yêu cầu tuyển dụng office”
- nhưng không nhất thiết phải sở hữu lâu dài một model riêng tên `recruitment.request`

Có thể có hai hướng kiến trúc hợp lý hơn:

- giữ business document riêng nhưng dùng approval chuẩn của Odoo
- hoặc chuyển hẳn phần header approval sang `approval.request`, chỉ giữ line/detail tuyển dụng riêng

Vì vậy, cách viết hiện tại nên chỉnh lại để tránh mâu thuẫn trong kết luận.

### 3.3. `candidate_email_template_id` nên được diễn đạt là “cần hợp nhất vai trò”, không nên kết luận bỏ ngay

Nội dung đề xuất hiện tại cho rằng:

- `candidate_email_template_id` trên stage chồng vai trò với `template_id` chuẩn của Odoo
- nên dùng field chuẩn

Định hướng này là đúng.

Tuy nhiên, nên diễn đạt thận trọng hơn:

- trước khi bỏ ngay `candidate_email_template_id`, cần rà kỹ xem nó có semantics riêng hay không

Hiện field custom nằm ở:

- [hr_recruitment_stage.py](d:\odoo-19.0+e.20250918\addons\M02_P0204_00\models\hr_recruitment_stage.py#L26)

Còn field chuẩn của Odoo nằm ở:

- [hr_recruitment_stage.py](d:\odoo-19.0+e.20250918\odoo\addons\hr_recruitment\models\hr_recruitment_stage.py#L19)

Do đó, kết luận phù hợp hơn nên là:

- cần hợp nhất về một field chuẩn nếu không còn khác biệt nghiệp vụ

thay vì khẳng định bỏ ngay lập tức.

### 3.4. Phần “template đánh giá dùng chung” là đúng hướng, nhưng chưa phản ánh trạng thái code hiện tại

Nội dung đề xuất nói:

- nên thống nhất một họ model interview evaluation dùng chung cho store và office
- nghiêng về giữ `hr.applicant.evaluation*`

Điều này là hợp lý về hướng chuẩn hóa.

Tuy nhiên, cần ghi rõ đây là:

- mục tiêu kiến trúc sau chuẩn hóa

chứ chưa phải trạng thái hiện tại.

Hiện tại:

- `0204` có `hr.applicant.oje.evaluation*`
- `0205` có `hr.applicant.evaluation*`

Và chưa thấy trong code hiện tại một họ `hr.applicant.interview.evaluation*` đang hoạt động song song như mô tả trong đoạn đề xuất.

Vì vậy phần này nên chỉnh để bám sát code thực tế hơn.

## 4. Kết luận

Nội dung đề xuất này phù hợp khoảng **80-85% về hướng kiến trúc**.

Các điểm đúng và nên giữ:

- `0204_00` làm base/shared, `0205` chỉ mở rộng office flow
- `is_pre_interview` chỉ nên có một owner duy nhất
- không nên redeclare `survey_id` của `hr.job` trong `0205`
- nên gom dần bộ form động của `0204` về property chuẩn Odoo
- nên giữ các model nghiệp vụ riêng như `interview.schedule`, `recruitment.plan*`, `recruitment.batch`, `oje evaluation`

Các điểm cần chỉnh trước khi coi là bản chốt:

- thêm `job.approval.request` của `0204` vào danh sách model thừa hoặc trùng chuẩn
- chỉnh lại cách nói về `recruitment.request` để không mâu thuẫn với hướng refactor sang `approval.request`
- với `candidate_email_template_id`, nên kết luận theo hướng “hợp nhất vai trò” thay vì “bỏ ngay”
- phần model evaluation dùng chung nên viết theo hướng mục tiêu sau chuẩn hóa, không nên mô tả như trạng thái hiện tại nếu code chưa đúng như vậy

## 5. Kết luận ngắn gọn

Nếu dùng nội dung này làm tài liệu định hướng kiến trúc thì hoàn toàn ổn.

Nếu dùng nó làm tài liệu “chốt phương án cuối cùng để triển khai refactor”, thì nên chỉnh lại vài điểm như trên để:

- sát code thực tế hơn
- tránh bỏ sót model trùng chuẩn ở `0204`
- tránh chốt quá mạnh ở những chỗ còn cần xác minh semantics

