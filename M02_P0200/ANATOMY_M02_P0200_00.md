# ANATOMY M02_P0200

## 1) Muc tieu module

`M02_P0200` la module master data/config nen cho cac module khac.
No dong vai tro:

- Bo sung field cho model core (`res.users`, `hr.employee`, `hr.department`, `hr.job`, `pos.config`).
- Cung cap bang danh muc dung chung cho HR va Restaurant operation.
- Tao seed data de co san cau truc phong ban, vi tri, cua hang, checklist.

## 2) Phan loai bang

### 2.1 Shared Config / Dimension (nen duoc ke thua dung lai)

- `department.block`
- `hr.job.level`
- `hr.job.position.default`
- `restaurant.area`
- `restaurant.positioning.area`
- `restaurant.station`
- `restaurant.shift`
- `shift.log.checklist` (master checklist)

### 2.2 Extension tren bang core Odoo (goi y cho module khac tiep tuc inherit)

- `res.users` (them `x_is_portal_manager`)
- `hr.employee` (them `legal_name`, `private_phone`)
- `hr.department` (them `block_id`, `pos_config_id`, `user_id`, `block_code`)
- `hr.job` (them `code`, `name_ll`, `level_id`)
- `pos.config` (them `store_code`, gio mo/dong cua, main/secondary shifts, `department_id`)

### 2.3 Transactional / Operational

- `shift.log`
- `shift.log.employee`
- `shift.log.checklist.line`

## 3) Quan he du lieu chinh

- `department.block` 1-n `hr.department` (`hr.department.block_id`)
- `department.block` 1-n `hr.job.position.default` (`block_id`)
- `hr.job.level` 1-n `hr.job.position.default` va 1-n `hr.job`
- `hr.department` 1-1 `res.users` (rang buoc unique `user_id`)
- `hr.department` n-1 `pos.config` qua `pos_config_id` (OPS mapping)
- `restaurant.area` 1-n `restaurant.positioning.area`
- `restaurant.positioning.area` 1-n `restaurant.station`
- `restaurant.shift` n-n `pos.config` qua:
  - `pos_config_main_shift_rel`
  - `pos_config_secondary_shift_rel`
- `shift.log` n-1 `pos.config`, n-1 `restaurant.shift`, n-1 `hr.employee` (MIC)
- `shift.log` 1-n `shift.log.employee`
- `shift.log` 1-n `shift.log.checklist.line`
- `shift.log.checklist.line` n-1 `shift.log.checklist` (master)

## 4) Seed data quan trong

- `data/hr_job_level_data.xml`: cap bac cong viec chuan.
- `data/department_block_data.xml`: khoi RST/OPS/SV + area/positioning/station + shift.
- `data/rst_department_data.xml`: phong ban khoi RST.
- `data/hr_job_position_default_data.xml`: bo vi tri mac dinh cho khoi OPS.
- `data/rst_job_data.xml`: danh sach `hr.job` cho khoi RST.
- `data/store_data.xml`: mapping cua hang POS <-> phong ban OPS.
- `data/shift_log_checklist_data.xml`: checklist master cho dau/giua/cuoi ca.
- `data/hr_master_data.xml`: user/employee mau + quan he hierarchy.

## 5) Config core dung chung cho module khac

Neu module khac can dung chung, uu tien tai su dung cac tru cot sau:

- Nhom to chuc:
  - `hr.department.block_id`
  - `hr.department.pos_config_id`
  - `hr.department.user_id`
- Nhom vi tri:
  - `hr.job.level_id`
  - `hr.job.code`
  - `hr.job.name_ll`
- Nhom van hanh cua hang:
  - `pos.config.store_code`
  - `pos.config.main_shift_ids`
  - `pos.config.secondary_shift_ids`
  - `pos.config.department_id`
- Nhom restaurant topology:
  - `restaurant.area` -> `restaurant.positioning.area` -> `restaurant.station`

## 6) Ràng buoc va rule dang co

- `department.block`: unique `code`
- `hr.department`: unique `user_id` (1 user chi gan 1 department)
- `hr.job.position.default`: unique (`code`, `block_id`)
- `hr.job`: unique (`code`, `department_id`, `company_id`)
- `restaurant.shift`: unique `code`
- `shift.log`: unique (`pos_config_id`, `date`, `shift_id`)

## 7) Extension points khuyen nghi

Neu ban muon module khac ke thua, nen tiep can theo thu tu:

1. Inherit `hr.department` neu can bo sung logic theo khoi/phong ban/POS.
2. Inherit `hr.job` hoac `hr.job.position.default` neu can bo sung metadata vi tri.
3. Inherit `pos.config` neu can them cau hinh van hanh theo cua hang.
4. Tai su dung `restaurant.shift`, `restaurant.station` de mapping planning/assignment/report.
5. Neu can luong giao dich, lay `shift.log` lam fact table.

## 8) Ghi chu khi maintain

- Du lieu seed dang kha lon (dac biet `rst_job_data.xml`, `store_data.xml`), khi doi ma/code can soat lai unique constraint.
- `hr_department.action_generate_positions()` dang auto copy tu `hr.job.position.default` theo `block_id`, phu hop cho co che setup nhanh.
- Co dau hieu mojibake (ky tu TV bi loi ma hoa) trong mot so label/help string. Khong anh huong logic, nhung nen chuan hoa UTF-8 khi can hien thi.
