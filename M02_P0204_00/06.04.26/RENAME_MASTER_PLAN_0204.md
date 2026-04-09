# Plan

## Phase 1: Chot taxonomy va dich doi ten

- Tach doi tuong trong `M02_P0204_00` thanh 2 nhom:
  - model goc dang `_inherit`: `hr.applicant`, `hr.job`, `hr.recruitment.stage`, `survey.survey`, `survey.question`, `survey.user_input`, `survey.user_input.line`, `hr.applicant.refuse.reason`, `applicant.get.refuse.reason`
  - model moi dang `_name`: `interview.schedule`, `hr.job.email.rule`, `hr.applicant.oje.evaluation*`, `hr.applicant.interview.evaluation*`, `applicant.get.refuse.reason.line`
- Rule ap dung:
  - model goc: giu nguyen ten
  - model moi: `x_psm_<ten_model>`
  - field moi tren model goc: `x_psm_0204_<tenfield>`
  - field moi tren model moi: `x_psm_<tenfield>`
  - action: `action_psm_<tenaction>`
  - view: `view_psm_<tenview>`
  - security nha hang: `group_gdh_ops_<module>_crw`, `group_gdh_ops_<module>_mgr`

## Phase 2: Inventory chi tiet va mapping trung tam

- Quet toan bo Python/XML/CSV de lap mapping `old -> new` cho:
  - model
  - field
  - action/view/menu/template XML ID
  - security group + ACL
- Chot 1 file mapping trung tam, dung xuyen suot cac phase sau.

## Phase 3: Chuan hoa security truoc

- Rename group theo rule nha hang:
  - `group_store_manager` -> `group_gdh_ops_0204_crw`
  - `group_operations_manager` -> `group_gdh_ops_0204_mgr`
- Cap nhat toan bo `groups=""`, ACL, rule va cac cho dung `has_group()`.
- Dat muc minimum permission, khong mo rong quyen khong can thiet.

## Phase 4: Chuan hoa action/view/menu/template XML ID

- Action doi sang `action_psm_*`.
- View doi sang `view_psm_*`.
- Menu/template de xuat dat tien to thong nhat de de truy vet.
- Cap nhat moi `ref`, `inherit_id`, `env.ref()`, menu action.

## Phase 5: Chuan hoa field tren model goc

- Doi field custom tren model goc sang `x_psm_0204_*`.
- Cap nhat dong bo Python, XML, domain/context, mail template, controller payload.
- Neu DB da co du lieu: phai kem migration (oldname/script SQL) truoc khi deploy.

## Phase 6: Chuan hoa model moi

- Doi `_name` model custom sang `x_psm_*`.
- Cap nhat toan bo:
  - relation string trong Many2one/One2many/Many2many
  - `ir.model.access.csv`
  - record rule
  - XML `model=""`
  - `env['model.name']`
  - `res_model` trong action/activity

## Phase 7: Migration tuong thich nguoc

- Bat buoc voi module da chay that:
  - migration cho model name
  - migration cho field name
  - migration cho XML ID
  - migration cho group XML ID
- Muc tieu: khong mat du lieu, khong vo `env.ref()`, khong vo phan quyen.

## Phase 8: Kiem thu sau rename

- Test upgrade module `M02_P0204_00`.
- Test backend: applicant/job/stage/OJE/interview evaluation.
- Test portal: schedule, OJE list, OJE form, interview confirmation.
- Test role-based access voi Store Manager, Ops Manager, HR User, HR Manager.

## Risk canh bao truoc khi code rename

- `interview.schedule` dang duoc tham chieu boi module khac:
  - `M02_P0204_01`
  - `M02_P0205_00`
- Vi vay, Phase 6 khong nen lam truc tiep neu chua co migration cross-module va regression test lien module.
