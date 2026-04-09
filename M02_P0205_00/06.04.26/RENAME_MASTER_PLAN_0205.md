# Plan

## Phase 1: Chot taxonomy va mapping dich

- Tach toan bo doi tuong cua `0205` thanh 2 nhom:
  - model goc dang `_inherit` nhu `hr.applicant`, `hr.job`, `hr.job.level`, `res.company`, `calendar.event`, `survey.survey`
  - model moi dang `_name` nhu `recruitment.request`, `recruitment.plan`, `recruitment.batch`, `hr.applicant.evaluation`...
- Chot rule ap dung:
  - model goc: giu nguyen ten
  - model moi: doi sang `x_psm_<ten_model>`
  - field moi tren model goc: `x_psm_0205_<tenfield>`
  - field moi tren model moi: `x_psm_<tenfield>`
  - action: `action_psm_<tenaction>`
  - view: `view_psm_<tenview>`
  - security van phong: `group_gdh_rst_<module>_stf`, `group_gdh_rst_<module>_mgr`

## Phase 2: Inventory chi tiet toan bo 0205

- Quet toan bo Python/XML/CSV de lap bang mapping `old -> new` cho:
  - model moi
  - field moi
  - XML ID cua action/view/menu/group/cron/sequence/template
  - security group va ACL
- Output phase nay la mot file mapping trung tam de dung xuyen suot cac phase sau.

## Phase 3: Doi ten security truoc

- Chuan hoa cac group hien co trong `approval_groups.xml` va `hr_validator_group.xml` ve format rule moi.
- Cap nhat toan bo `groups=""`, `has_group()`, `ACL CSV` va `rule XML`.
- Dong thoi ra lai minimum permission vi rule moi nhan manh quyen toi thieu.

## Phase 4: Doi ten action, view, menu, template, sequence, cron

- Rename toan bo XML ID ky thuat sang chuan `action_psm_*`, `view_psm_*` va prefix thong nhat cho menu/template/cron/sequence.
- Cap nhat moi `ref`, `inherit_id`, `env.ref()`, menu action va template inheritance.

## Phase 5: Chuan hoa field tren model goc

- Cac field them vao `hr.applicant`, `hr.job`, `hr.job.level`, `res.company`, `calendar.event`, `survey.survey`... doi sang `x_psm_0205_*`.
- Cap nhat lai Python, XML view, domain/context, mail template, survey data va script logic co dung field cu.
- Neu DB da co du lieu that, phase nay phai di kem migration du lieu field.

## Phase 6: Chuan hoa model moi

- Doi cac `_name` model custom sang `x_psm_<ten_model>`.
- Cap nhat toan bo:
  - `Many2one`, `One2many`, `Many2many`
  - `ir.model.access.csv`
  - `record rules`
  - XML `model=""`
  - `env['model.name']`
  - `mail/activity/tracking references`
- Day la phase rui ro cao nhat nen lam sau khi security, action/view va field da on.

## Phase 7: Chuan hoa theo rule dung chung

- Nhung phan lien quan duyet phai uu tien dung chung `approval`.
- Nhung phan khao sat/phong van/cau hoi phai uu tien dung chung `survey`.
- Cac ten nghiep vu phai thong nhat `applicant`, `employee`, tranh tao bien the khac.

## Phase 8: Migration va tuong thich nguoc

- Tao lop migration cho XML ID cu, model cu, field cu va group cu de upgrade tren DB hien co.
- Muc tieu la tranh gay du lieu, gay `env.ref()` va gay phan quyen khi nang cap module.

## Phase 9: Kiem thu sau rename

- Test upgrade module.
- Test form/tree/search/menu/button/action.
- Test role-based access.
- Test cac luong `request / plan / batch / applicant / evaluation / survey / portal`.
