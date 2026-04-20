# CONFIG TABLE CATALOG - M02_P0200

## `department.block`

- Vai tro: Danh muc khoi phong ban (RST/OPS/SV).
- Truong chinh: `name`, `code`, `active`.
- Rang buoc: unique `code`.
- Duoc tham chieu boi:
  - `hr.department.block_id`
  - `hr.job.position.default.block_id`

## `hr.job.level`

- Vai tro: Danh muc cap bac chung cho job.
- Truong chinh: `name`, `code`, `sequence`, `active`.
- Duoc tham chieu boi:
  - `hr.job.level_id`
  - `hr.job.position.default.level_id`

## `hr.job.position.default`

- Vai tro: Template vi tri mac dinh theo khoi (nhat la OPS), dung de sinh `hr.job`.
- Truong chinh: `name`, `name_ll`, `code`, `block_id`, `contract_type_id`, `level_id`, `sequence`, `active`.
- Rang buoc: unique (`code`, `block_id`).
- Logic lien quan:
  - `hr.department.action_generate_positions()` doc bang nay de tao `hr.job` cho phong ban.

## `restaurant.area`

- Vai tro: Danh muc khu vuc lon trong nha hang.
- Truong chinh: `name`, `code`.
- Quan he:
  - 1-n voi `restaurant.positioning.area` qua `positioning_area_ids`.

## `restaurant.positioning.area`

- Vai tro: Danh muc khu vuc nho trong tung khu vuc lon.
- Truong chinh: `name`, `area_id`.
- Quan he:
  - n-1 `restaurant.area`
  - 1-n `restaurant.station`

## `restaurant.station`

- Vai tro: Danh muc station chi tiet de phan cong van hanh.
- Truong chinh: `name`, `code`, `positioning_area_id`, `menu_type`.
- Quan he:
  - n-1 `restaurant.positioning.area`

## `restaurant.shift`

- Vai tro: Danh muc ca lam viec dung chung.
- Truong chinh: `name`, `code`, `hour_from`, `hour_to`.
- Rang buoc: unique `code`.
- Duoc tham chieu boi:
  - `pos.config.main_shift_ids`
  - `pos.config.secondary_shift_ids`
  - `shift.log.shift_id`

## `shift.log.checklist`

- Vai tro: Master checklist cho cac phase ca lam (`preshift`, `during`, `postshift`).
- Truong chinh: `name`, `shift_phase`, `category`, `sequence`, `description`.
- Duoc tham chieu boi:
  - `shift.log.checklist.line.checklist_id`

## Config field bo sung tren bang core

### `hr.department` (extend)

- Field config:
  - `block_id` (phan loai khoi)
  - `pos_config_id` (gan cua hang POS cho OPS)
  - `user_id` (tai khoan dai dien phong ban/cua hang)
  - `block_code` (related)
- Rang buoc:
  - unique `user_id`

### `hr.job` (extend)

- Field config:
  - `code`
  - `name_ll`
  - `level_id`
- Rang buoc:
  - unique (`code`, `department_id`, `company_id`)

### `pos.config` (extend)

- Field config:
  - `store_code`
  - `opening_hour`, `closing_hour`
  - `main_shift_ids`, `secondary_shift_ids`
  - `department_id` (compute theo `hr.department.pos_config_id`)

### `res.users` (extend)

- Field config:
  - `x_is_portal_manager` (danh dau vai tro quan ly cho portal flow)

### `hr.employee` (extend)

- Field bo sung:
  - `legal_name`
  - `private_phone`

## Bang transaction de phan biet

- `shift.log`: du lieu van hanh theo ngay-ca-cua hang.
- `shift.log.employee`: nhan vien tham gia trong tung shift log.
- `shift.log.checklist.line`: ket qua checklist theo tung shift log.

## Goi y tai su dung cho module ke thua

1. Module xin phep/approval theo cua hang:
   - Dung `hr.department.pos_config_id` + `department.block`.
2. Module planning/roster:
   - Dung `restaurant.shift` + `pos.config.main_shift_ids` / `secondary_shift_ids`.
3. Module phan cong cong viec tai station:
   - Dung `restaurant.area`/`restaurant.positioning.area`/`restaurant.station`.
4. Module tu dong tao vi tri:
   - Dung `hr.job.position.default` + `action_generate_positions()`.
