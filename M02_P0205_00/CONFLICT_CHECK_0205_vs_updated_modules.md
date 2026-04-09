# Kiểm tra xung đột `M02_P0205_00` với danh sách module vừa cập nhật

**Ngày kiểm tra:** 2026-04-03

## Kết luận nhanh

- Không thấy xung đột cài đặt trực tiếp với đa số module trong danh sách bạn đưa.
- Điểm overlap lớn nhất nằm giữa `M02_P0205_00` và `M02_P0211_00` trên model `hr.applicant`.
- Có overlap UI nhẹ giữa `M02_P0205_00` và `M02_P0209_03` trên model `hr.job`.
- Các module còn lại chủ yếu chạm các model khác hoặc thêm field riêng, chưa thấy trùng field/method đủ để tạo conflict cứng.

## Điểm xung đột đáng chú ý nhất

### `M02_P0205_00` vs `M02_P0211_00`

- `M02_P0205_00` đang khai báo phụ thuộc vào `M02_P0211_00`, nên `0211` được load trước và `0205` load sau: [addons/M02_P0205_00/__manifest__.py](./__manifest__.py)
- Hai module cùng định nghĩa một cụm lớn trên `hr.applicant`:
  - `document_approval_status`
  - `passport_photo`
  - `id_card_front`
  - `id_card_back`
  - `household_registration`
  - `judicial_record`
  - `professional_certificate`
  - `additional_certificates`
  - `portal_last_update`
  - `portal_updates_count`
  - `action_approve_documents`
  - `action_refuse_documents`
- Do `0205` load sau, phần logic trùng sẽ có tính chất ghi đè/đi tiếp behavior hơn là lỗi install ngay.
- Đây là overlap có chủ ý, nhưng là vùng rủi ro cao nhất nếu server vừa cập nhật `0211` với logic khác.

Tham chiếu:
- [addons/M02_P0205_00/models/hr_applicant.py](./models/hr_applicant.py)
- [addons/M02_P0211_00/models/hr_applicant.py](../M02_P0211_00/models/hr_applicant.py)

## Overlap nhẹ trên `hr.job`

### `M02_P0205_00` vs `M02_P0209_03`

- `0205` inherit `hr.job` để thêm:
  - `current_employee_count`
  - `needed_recruitment`
  - `is_office_job`
  - `survey_id`
  - các helper/liên quan portal
- `0209_03` cũng inherit `hr.job`, nhưng chỉ thêm:
  - `station_ids`
  - `manager_station_ids`
- Hai module cùng chèn vào form `hr.view_hr_job_form`, nhưng vào các vị trí/field khác nhau nên đây là overlap layout, chưa phải xung đột cứng.

Tham chiếu:
- [addons/M02_P0205_00/models/hr_job.py](./models/hr_job.py)
- [addons/M02_P0205_00/views/hr_job_views.xml](./views/hr_job_views.xml)
- [addons/M02_P0209_03/models/job_position.py](../M02_P0209_03/models/job_position.py)
- [addons/M02_P0209_03/views/hr_job_views.xml](../M02_P0209_03/views/hr_job_views.xml)

## Các module khác trong danh sách

### `M02_P0202_04`

- Có inherit `hr.job` và `hr.applicant`, nhưng field chính là:
  - `referral_reward`
  - `is_reward_paid`
  - `reward_paid_amount`
  - `reward_pending_amount`
- Không thấy trùng trực tiếp với cụm field/method của `0205`.

Tham chiếu:
- [addons/M02_P0202_04/models/hr_job.py](../M02_P0202_04/models/hr_job.py)
- [addons/M02_P0202_04/models/hr_applicant.py](../M02_P0202_04/models/hr_applicant.py)

### `M02_P0217_00`

- Có inherit `hr.job`, nhưng chỉ thêm `crew_survey_id`.
- Không thấy đụng trực tiếp vào field/method của `0205`.

Tham chiếu:
- [addons/M02_P0217_00/models/hr_job.py](../M02_P0217_00/models/hr_job.py)
- [addons/M02_P0217_00/views/hr_job_views.xml](../M02_P0217_00/views/hr_job_views.xml)

### `M02_P0218_01` và `M02_P0219_00`

- Hai module này tập trung vào `hr.appraisal`, `survey`, `behavior.question`, không chạm trực tiếp `hr.applicant` theo kiểu conflict với `0205`.
- Chúng có `hr.job` gián tiếp qua config/survey, nhưng không thấy trùng field trực tiếp với `0205`.

Tham chiếu:
- [addons/M02_P0218_01/models/hr_appraisal.py](../M02_P0218_01/models/hr_appraisal.py)
- [addons/M02_P0219_00/models/hr_appraisal.py](../M02_P0219_00/models/hr_appraisal.py)

### `M02_P0211_00` portal/onboarding

- `0211` có portal onboarding riêng:
  - `/my/onboard_info`
  - `/my/contract`
  - template inherit riêng trên `portal_custom.portal_my_home_inherit`
- `0205` dùng portal recruitment riêng:
  - `/my/jobs`
  - `/my/recruitment_requests`
- Không trùng template id, nên đây là song song hơn là đạp nhau trực tiếp.

Tham chiếu:
- [addons/M02_P0205_00/views/portal_templates.xml](./views/portal_templates.xml)
- [addons/M02_P0211_00/views/portal_templates.xml](../M02_P0211_00/views/portal_templates.xml)

## Nhận định thực tế

- Nếu bạn hỏi “có lỗi cài đặt không?” thì hiện tại chưa thấy dấu hiệu chắc chắn của lỗi cứng.
- Nếu bạn hỏi “có chỗ nào dễ bị đè logic sau khi server cập nhật không?” thì có, và đó là:
  1. `hr.applicant` giữa `0205` và `0211`
  2. `hr.job` giữa `0205` và `0209_03`
  3. `hr.job` giữa `0205` và `0202_04`, nhưng overlap chủ yếu là cùng form và cùng model, không thấy trùng field quan trọng

## Gợi ý xử lý

1. Giữ `0205` là nơi sở hữu logic recruitment office nếu đây là module chính.
2. Đảm bảo `0211` chỉ giữ logic onboarding, không định nghĩa lại cùng tên field/method nếu không thật sự cần.
3. Với `0209_03`, `0202_04`, `0217_00`, nên kiểm tra thứ tự load view nếu thấy field hiển thị sai vị trí.
4. Nếu muốn an toàn hơn, nên tách file ghi chú này thành checklist theo từng model:
   - `hr.applicant`
   - `hr.job`
   - portal template
   - controller route

