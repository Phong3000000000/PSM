# Test Guide: Survey Digital Marketing Executive

## Mục tiêu

Hướng dẫn kiểm thử survey:

- `Khảo sát năng lực - Digital Marketing Executive`
- xml nguồn: `addons/M02_P0205/data/survey_digital_marketing_executive.xml`

Tài liệu này giúp dev test nhanh 3 nhánh:

- `PASS`
- `CONSIDER`
- `FAIL`

## Tổng quan logic chấm

Survey này đang chạy theo logic trong `survey_ext.py`:

- nếu điểm `Must Have` dưới ngưỡng `70%` -> `FAIL`
- nếu đạt ngưỡng `Must Have` nhưng không có đáp án `Nice to Have` nào -> `CONSIDER`
- nếu đạt ngưỡng `Must Have` và có ít nhất 1 đáp án `Nice to Have` -> `PASS`

## Các đáp án quan trọng

### Must Have

- Câu 1:
  - `Facebook Ads`
  - `Google Ads`
- Câu 2:
  - `Kiểm tra lại target, nội dung và chỉ số chuyển đổi trước khi tăng ngân sách`
- Câu 3:
  - `CTR`
  - `CPC / CPM`
- Câu 4:
  - `Meta Ads Manager / Google Ads / GA4`

### Nice to Have

- Câu 1:
  - `Email Marketing / Automation`
- Câu 3:
  - `ROAS`
- Câu 4:
  - `Đã từng xem dashboard Looker Studio hoặc báo cáo tổng hợp`

## Kịch bản test

## Case 1. PASS

### Mục tiêu

Đưa applicant vào nhánh `PASS`.

### Cách chọn đáp án

- Câu 1:
  - chọn `Facebook Ads`
  - chọn `Google Ads`
  - chọn thêm `Email Marketing / Automation`
- Câu 2:
  - chọn `Kiểm tra lại target, nội dung và chỉ số chuyển đổi trước khi tăng ngân sách`
- Câu 3:
  - chọn `CTR`
  - chọn `CPC / CPM`
  - chọn thêm `ROAS`
- Câu 4:
  - chọn `Meta Ads Manager / Google Ads / GA4`
  - hoặc chọn `Đã từng xem dashboard Looker Studio hoặc báo cáo tổng hợp`
- Câu 5:
  - nhập nội dung bất kỳ

### Kỳ vọng

- survey hoàn tất với điểm `Must Have` đạt ngưỡng
- có ít nhất 1 đáp án `Nice to Have`
- applicant vào `Screening`
- hệ thống post message kết quả `PASS`
- có activity:
  - `Kiểm tra CV ứng viên sau khi PASS khảo sát`

## Case 2. CONSIDER

### Mục tiêu

Đưa applicant vào nhánh `CONSIDER`.

### Cách chọn đáp án

- Câu 1:
  - chọn `Facebook Ads`
  - chọn `Google Ads`
  - không chọn `Email Marketing / Automation`
- Câu 2:
  - chọn `Kiểm tra lại target, nội dung và chỉ số chuyển đổi trước khi tăng ngân sách`
- Câu 3:
  - chọn `CTR`
  - chọn `CPC / CPM`
  - không chọn `ROAS`
- Câu 4:
  - chọn `Meta Ads Manager / Google Ads / GA4`
  - không chọn `Đã từng xem dashboard Looker Studio hoặc báo cáo tổng hợp`
- Câu 5:
  - nhập nội dung bất kỳ

### Kỳ vọng

- survey đạt ngưỡng `Must Have`
- không có đáp án `Nice to Have`
- applicant vào `Screening`
- hệ thống post message kết quả `CONSIDER`
- có activity:
  - `Rà soát ứng viên nhánh CONSIDER`

## Case 3. FAIL

### Mục tiêu

Đưa applicant vào nhánh `FAIL`.

### Cách chọn đáp án

- Câu 1:
  - chỉ chọn `Content / Social`
  - không chọn `Facebook Ads`
  - không chọn `Google Ads`
- Câu 2:
  - chọn `Tăng ngân sách để kéo thêm traffic rồi đo tiếp`
- Câu 3:
  - không chọn `CTR`
  - không chọn `CPC / CPM`
  - có thể chỉ chọn `Conversion Rate / CPA` hoặc bỏ ở mức tối thiểu theo UI
- Câu 4:
  - chọn `Chủ yếu theo dõi thủ công, chưa quen các công cụ`
- Câu 5:
  - nhập nội dung bất kỳ

### Kỳ vọng

- điểm `Must Have` dưới `70%`
- applicant vào `Reject`
- hệ thống post message kết quả `FAIL`
- nếu cấu hình email từ chối đang hoạt động, applicant nhận mail từ chối khảo sát

## Checklist kiểm thử trên applicant

1. Gán survey này vào job `Digital Marketing Executive`.
2. Tạo applicant mới cho job đó.
3. Gửi survey cho applicant.
4. Làm survey theo từng case ở trên.
5. Sau khi submit, kiểm tra:
- `stage_id`
- chatter message
- `survey_result_url`
- activity follow-up
- mail từ chối nếu test case `FAIL`

## Kết quả mong đợi theo nhánh

- `PASS`
  - stage: `Screening`
  - activity: `Kiểm tra CV ứng viên sau khi PASS khảo sát`
- `CONSIDER`
  - stage: `Screening`
  - activity: `Rà soát ứng viên nhánh CONSIDER`
- `FAIL`
  - stage: `Reject`
  - không có activity review screening

## Ghi chú

- Câu 5 là câu text, không ảnh hưởng trực tiếp tới pass/fail.
- Khi test `CONSIDER`, điểm mấu chốt là:
  - phải đạt đủ `Must Have`
  - đồng thời không chọn bất kỳ đáp án `Nice to Have` nào
- Khi test `PASS`, chỉ cần có ít nhất 1 `Nice to Have` sau khi đã đạt `Must Have`.
