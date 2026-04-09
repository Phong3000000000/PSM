# Agenda 0205

## 1. Quy trinh

Module `M02_P0205_00` phuc vu quy trinh tuyen dung khoi Van phong, mo rong tren nen `hr_recruitment` va dung chung mot so logic voi module nen `M02_P0204_00`.

### 1.1. Pham vi chinh

- Quan ly Yeu cau tuyen dung.
- Quan ly Ke hoach tuyen dung va Ke hoach con theo phong ban.
- Gom vi tri vao Dot tuyen dung.
- Dang Job len website/portal.
- Gui bai test nang luc truoc phong van.
- Quan ly nhieu vong phong van: Manager, CEO, BOD, ABU.
- Danh gia ung vien, gui offer, chot trung tuyen.

### 1.2. Luong nghiep vu tong quan

1. Don vi tao Yeu cau tuyen dung.
2. HR validate yeu cau.
3. CEO phe duyet yeu cau.
4. He thong tang `no_of_recruitment` cho Job va co the dang Job len website.
5. HR lap Ke hoach tuyen dung tong.
6. He thong tach Ke hoach con theo phong ban va gui activity cho Truong phong.
7. Truong phong duyet Ke hoach con.
8. HR validate ke hoach.
9. CEO duyet ke hoach hoac duyet theo Dot tuyen dung.
10. He thong dang tin va dua Ke hoach vao trang thai `in_progress`.
11. Ung vien nop don tu website/portal hoac duoc tao thu cong.
12. Gui survey pre-interview theo Job.
13. Ung vien lam bai test, he thong cap nhat ket qua va day sang Screening.
14. HR/nguoi phu trach review CV.
15. Moi va sap lich cac vong phong van.
16. Interviewer danh gia theo tung vong.
17. Du ung vien sang cac vong tiep theo hoac gui offer.
18. Xac nhan signed, hoan tat va lien ket onboarding/offboarding khi can.

### 1.3. Trang thai chinh

#### Yeu cau tuyen dung (`recruitment.request`)

- `draft`
- `hr_validation`
- `ceo_approval`
- `in_progress`
- `done`
- `cancel`

#### Ke hoach tuyen dung (`recruitment.plan`)

- `draft`
- `waiting_manager`
- `manager_approved`
- `hr_validation`
- `waiting_ceo`
- `in_progress`
- `done`
- `cancel`

#### Dot tuyen dung (`recruitment.batch`)

- `draft`
- `open`
- `waiting_ceo`
- `approved`
- `closed`

### 1.4. Tu dong hoa dang chu y

- Tu dong sinh sequence cho Yeu cau, Ke hoach va Dot.
- Tu dong tao Ke hoach con theo phong ban tu Ke hoach tong.
- Tu dong gui `mail.activity` cho HR, CEO, Truong phong.
- Tu dong dang Job len website/portal khi da duoc duyet.
- Tu dong nhac Truong phong qua cron neu cham duyet.
- Tu dong thong bao khi den thang can tuyen.
- Tu dong publish Dot duoc duyet khi den `date_start`.

## 2. Models, fields, action, views...

## 2.1. Models chinh

### Model moi

- `recruitment.request`: Yeu cau tuyen dung.
- `recruitment.request.line`: Dong chi tiet vi tri can tuyen.
- `recruitment.request.approver`: Danh sach nguoi duyet theo phong ban.
- `recruitment.plan`: Ke hoach tuyen dung tong/ke hoach con.
- `recruitment.plan.line`: Dong chi tiet cua ke hoach.
- `recruitment.batch`: Dot tuyen dung.
- `hr.applicant.evaluation`: Phieu danh gia phong van.
- `hr.applicant.evaluation.line`: Tieu chi cham diem chi tiet.

### Model mo rong

- `hr.applicant`: bo sung survey, phong van, evaluation, offer, tai lieu ho so.
- `hr.job`: bo sung survey theo job, noi dung website, interviewer mac dinh.
- `survey.survey`: bo sung co `is_pre_interview`.
- `survey.question.answer`: bo sung `is_must_have`, `is_nice_to_have`.
- `mail.activity`: khi done activity co noi dung CV PASS thi danh dau `cv_checked`.
- `res.company`: dung cho cau hinh CEO va thong tin phe duyet lien quan.

## 2.2. Field noi bat

### `recruitment.request`

- `request_type`: `unplanned` hoac `planned`.
- `job_id`, `department_id`, `quantity`, `date_start`, `date_end`, `reason`.
- `line_ids`: danh sach vi tri can tuyen.
- `approver_ids`: danh sach manager duyet.
- `recruitment_plan_id`: lien ket voi Ke hoach.
- `state`, `is_published`.

### `recruitment.plan`

- `line_ids`: danh sach nhu cau can tuyen.
- `priority`, `reason`, `state`.
- `parent_id`, `sub_plan_ids`, `department_id`, `is_sub_plan`.
- `request_count`, `job_count`, `total_quantity`.
- `batch_id`, `date_submitted`, `is_reminder_sent`.
- `can_approve_as_manager`: chi mo nut duyet dung nguoi.

### `recruitment.plan.line`

- `department_id`, `job_id`, `quantity`, `planned_date`, `reason`.
- `is_approved`: Truong phong bo tick dong nao thi dong do bi loai khi duyet.
- `applicant_count`, `interview_count`, `hired_count`.
- `is_published`.

### `recruitment.batch`

- `batch_name`, `date_start`, `date_end`, `state`.
- `line_ids`: tap hop vi tri da duyet ke hoach dua vao dot.

### `hr.job`

- `survey_id`: bai test nang luc theo vi tri.
- `job_intro`, `responsibilities`, `must_have`, `nice_to_have`, `whats_great`.
- `current_employee_count`, `needed_recruitment`, `is_office_job`.

### `hr.applicant`

- `application_source`: nguon ung vien.
- `document_approval_status`: cho duyet, da duyet, khong duyet.
- `survey_sent`, `survey_result_url`.
- `interview_date_1` den `interview_date_4`.
- `interview_result_1` den `interview_result_4`.
- Cac thong tin slot phong van, evaluator, offer, ky hop dong, tai lieu ung vien.

### `hr.applicant.evaluation`

- Luu phieu danh gia theo tung vong phong van.
- Sinh san template tieu chi cham diem.
- Dong bo ket qua danh gia vao applicant de quyet dinh qua vong.

## 2.3. Action nghiep vu chinh

### Tren Yeu cau tuyen dung

- `action_submit`: gui HR validate.
- `action_hr_validate`: chuyen CEO duyet.
- `action_ceo_approve`: duyet va chuyen `in_progress`.
- `action_publish_jobs`: dang Job len website.
- `action_open_job_page`: mo trang jobs.

### Tren Ke hoach tuyen dung

- `action_notify_department_heads`: gui thong bao va tao Ke hoach con.
- `action_manager_approve`: Truong phong duyet.
- `action_hr_validate`: HR validate.
- `action_ceo_approve`: CEO duyet.
- `action_publish_jobs`: dang tin.
- `action_view_sub_plans`, `action_open_jobs`.

### Tren Dot tuyen dung

- `action_open_batch`: mo dot.
- `action_pull_approved_lines`: keo cac vi tri da duyet vao dot.
- `action_send_ceo`: gui CEO duyet dot.
- `action_ceo_approve_batch`: CEO phe duyet dot.
- `action_close`, `action_reopen`.

### Tren Ung vien

- `action_send_survey`: gui bai test nang luc.
- `action_view_survey_result`: xem ket qua survey.
- `action_invite_interview_l1` den `action_invite_interview_l4`.
- `action_start_eval_l1` den `action_start_eval_l4`.
- `action_ready_for_offer`, `action_send_offer`, `action_confirm_signed`.
- `action_approve_documents`, `action_reject_documents`.

## 2.4. Views va giao dien

Module co cac man hinh chinh sau:

- `recruitment_plan_views.xml`: list/form/search cho Ke hoach, Ke hoach con, Dot tuyen dung.
- `recruitment_request_views.xml`: list/form cho Yeu cau tuyen dung.
- `recruitment_request_approver_views.xml`: man hinh nguoi duyet yeu cau.
- `hr_applicant_views.xml`: mo rong form ung vien, survey, interview, evaluation, offer.
- `hr_job_views.xml`: bo sung tab survey va noi dung website cho Job.
- `survey_views.xml`: bo sung field danh dau survey pre-interview.
- `res_company_views.xml`: cau hinh cong ty/CEO.
- `portal_templates.xml`, `job_portal_templates.xml`, `website_hr_recruitment_templates.xml`: giao dien website va portal tuyen dung.

### Menu chinh

- `Tuyen Dung VP`
- `Ke hoach Tuyen dung`
- `Ke hoach Con`
- `Dot Tuyen dung`

Ngoai ra, mot so menu duoc gan them vao root menu cua `hr_recruitment` de HR thao tac nhanh.

## 3. Phan quyen

## 3.1. Nhom quyen

Module khai bao them cac group:

- `group_hr_validator`: nhom HR Validator.
- `group_ceo_recruitment`: nhom CEO Recruitment Approver.
- `group_bod_recruitment`: nhom BOD Recruitment Viewer.
- `group_abu_recruitment`: nhom ABU Recruitment Control.

Cac group tren deu imply `hr.group_hr_manager`, nen ve ban chat la cac quyen chuyen vai tro tren nen HR.

## 3.2. Access rights

Trong `ir.model.access.csv`, cac model chinh deu dang cap quyen CRUD cho:

- `base.group_user`
- `hr_recruitment.group_hr_recruitment_manager`

Dieu nay co nghia:

- User noi bo co the doc/tao/sua/xoa tren nhieu model custom cua module.
- HR Recruitment Manager cung co day du CRUD.
- Survey duoc gioi han che hon: user chi doc, khong sua/xoa qua access file nay.

## 3.3. Phan quyen nghiep vu thuc te

Mac du access CSV kha rong, quyen thao tac thuc te duoc dieu tiet tiep trong code:

- Truong phong chi thay nut duyet khi `can_approve_as_manager = True`.
- Ke hoach con chi cho manager cua phong ban tuong ung duyet.
- HR Validator la nhom nhan activity khi Yeu cau/Ke hoach can HR validate.
- CEO Recruitment Approver la nhom nhan activity va thuc hien buoc CEO duyet.
- BOD va ABU duoc dua vao danh sach interviewer mac dinh cho office job.

## 3.4. Rule va luu y

- Module co sua `hr.hr_job_comp_rule` de Job dang `website_published = True` van doc duoc qua rule multi-company.
- Chua thay bo record rule noi bo chi tiet cho tung phong ban trong module nay.
- Vi access dang kha mo, neu can siet quyen theo don vi/nghiem thu, nen bo sung record rule o buoc tiep theo.

## 4. Su dung AI ntn?

Phan nay hien tai la de xuat ap dung. Trong code cua module `0205` chua thay tich hop AI thuc su.

## 4.1. Nen dung AI o dau

### Tao va chuan hoa noi dung

- Viet mo ta cong viec tu `job_intro`, `responsibilities`, `must_have`, `nice_to_have`.
- Goi y noi dung dang tuyen tren website/portal.
- Tao email moi phong van, email gui survey, email offer theo tung vai tro.

### Ho tro sang loc ung vien

- Tom tat CV ung vien theo mau ngan gon.
- Rut trich ky nang, so nam kinh nghiem, bang cap, chung chi.
- So khop CV voi `must_have` va `nice_to_have` cua Job.
- Goi y muc do phu hop: cao, trung binh, thap.

### Ho tro phong van

- Goi y bo cau hoi phong van theo tung Job va tung round.
- Tom tat diem manh, diem yeu tu phieu danh gia.
- Tong hop ket qua nhieu interviewer thanh de xuat chung.

### Bao cao va canh bao

- Du doan nguy co cham tien do tuyen.
- Goi y vi tri kho tuyen dua tren funnel `applicant_count`, `interview_count`, `hired_count`.
- Phat hien mo ta cong viec thieu thong tin hoac yeu cau chua ro rang.

## 4.2. Cach dung AI an toan

- AI chi nen dong vai tro tro ly, khong thay the phe duyet cua Manager, HR, CEO.
- Khong dua du lieu nhay cam cua ung vien len dich vu AI neu chua co chinh sach bao mat ro rang.
- Nen an/ma hoa thong tin CCCD, giay to, email, so dien thoai truoc khi gui AI.
- Can log ro prompt, ket qua va nguoi phe duyet neu AI duoc dua vao quy trinh van hanh.

## 4.3. De xuat lo trinh tich hop AI cho 0205

1. Giai doan 1: AI viet mo ta Job va email template.
2. Giai doan 2: AI tom tat CV va match voi Job.
3. Giai doan 3: AI tong hop ket qua phong van va de xuat next step.
4. Giai doan 4: AI dashboard canh bao tien do Dot/Ke hoach tuyen dung.

## 4.4. Nguyen tac khi demo voi business

- Noi ro phan nao la he thong dang co.
- Noi ro phan nao la AI de xuat them.
- Moi ket luan tuyen dung van phai do nguoi co tham quyen quyet dinh.

## 5. Ket luan ngan

`0205` la module quan ly tuyen dung khoi Van phong theo luong tu nhu cau -> ke hoach -> dot -> dang tin -> survey -> phong van nhieu vong -> offer -> hoan tat.

The manh cua module la:

- Co luong duyet ro rang.
- Co tach ke hoach theo phong ban.
- Co website/portal va survey.
- Co danh gia nhieu vong.
- Co kha nang mo rong de tich hop AI o cac buoc tao noi dung, sang loc va tong hop ket qua.
