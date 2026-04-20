from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class SignRequest(models.Model):
    _inherit = 'sign.request'

    def write(self, vals):
        res = super().write(vals)

        # Trạng thái tổng quát của tài liệu chuyển sang 'signed' (tất cả mọi người đã ký)
        if 'state' in vals and vals['state'] == 'signed':
            # Xác định các template (Dùng env.ref an toàn)
            contract_template = self.env.ref('M02_P0211.sign_template_contract', raise_if_not_found=False)
            handover_template = self.env.ref('M02_P0212_00.sign_template_handover', raise_if_not_found=False)

            for req in self:
                # Tìm nhân viên liên quan: 
                # Cách 1: Theo trường x_psm_0211_contract_sign_request_id (Chính xác nhất)
                # Cách 2: Theo partner của những người ký (Dự phòng)
                
                employee = self.env['hr.employee'].sudo().search([
                    ('x_psm_0211_contract_sign_request_id', '=', req.id)
                ], limit=1)

                if not employee:
                    # Fallback: Tìm theo partner của các items trong request
                    partners = req.request_item_ids.mapped('partner_id')
                    employee = self.env['hr.employee'].sudo().search([
                        '|',
                        ('user_partner_id', 'in', partners.ids),
                        ('work_contact_id', 'in', partners.ids)
                    ], limit=1)

                if not employee:
                    continue

                # 1. Nếu là mẫu Hợp đồng lao động (Dùng chung cho cả OPS và RST)
                if contract_template and req.template_id == contract_template:
                    _logger.info("SignRequest: Matched Contract for employee %s", employee.name)
                    employee.sudo().write({'x_psm_0211_onboarding_state': 'signed'})
                    employee.message_post(body="🖋️ Official Contract signed. Status transitioned to 'Signed'.")

                # 2. Nếu là mẫu Bàn giao thiết bị (Chỉ logic cho RST nằm ở 0212)
                if handover_template and req.template_id == handover_template:
                    _logger.info("SignRequest: Matched Handover for employee %s", employee.name)
                    # Trường x_psm_0212_handover_signed chỉ tồn tại nếu cài module 0212
                    if 'x_psm_0212_handover_signed' in employee._fields:
                        employee.sudo().write({'x_psm_0212_handover_signed': True})
                        employee.message_post(body="✅ Equipment Handover document signed. Handover checkbox updated.")

        return res


class SignRequestItem(models.Model):
    _inherit = 'sign.request.item'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not records:
            return records

        for item in records:
            if not item.partner_id:
                continue

            # Tìm nhân viên liên kết với partner này
            employee = self.env['hr.employee'].sudo().search([
                '|',
                ('user_partner_id', '=', item.partner_id.id),
                ('work_contact_id', '=', item.partner_id.id),
            ], limit=1)

            if not employee:
                continue

            # Auto-prefill logic
            company_item = self.env.ref('M02_P0211.sign_item_company_name', raise_if_not_found=False)
            name_item = self.env.ref('M02_P0211.sign_item_employee_name_signature', raise_if_not_found=False)

            values_to_create = []
            if company_item:
                values_to_create.append({
                    'sign_request_item_id': item.id,
                    'sign_item_id': company_item.id,
                    'value': employee.company_id.name or '',
                })
            if name_item:
                values_to_create.append({
                    'sign_request_item_id': item.id,
                    'sign_item_id': name_item.id,
                    'value': employee.name,
                })

            if values_to_create:
                self.env['sign.request.item.value'].sudo().create(values_to_create)

            # Cập nhật tham chiếu ngược từ employee sang sign.request
            contract_template = self.env.ref('M02_P0211.sign_template_contract', raise_if_not_found=False)
            handover_template = self.env.ref('M02_P0212_00.sign_template_handover', raise_if_not_found=False)
            
            if contract_template and item.sign_request_id.template_id == contract_template:
                employee.sudo().x_psm_0211_contract_sign_request_id = item.sign_request_id.id
            
            # Logic riêng cho mẫu Bàn giao (0212)
            if handover_template and item.sign_request_id.template_id == handover_template:
                # 1. Điền thông tin (Prefill)
                name_item_rst = self.env.ref('M02_P0212_00.sign_item_handover_employee_name', raise_if_not_found=False)
                company_item_rst = self.env.ref('M02_P0212_00.sign_item_handover_company_name_placeholder', raise_if_not_found=False)
                
                v_create = []
                if company_item_rst:
                    v_create.append({
                        'sign_request_item_id': item.id,
                        'sign_item_id': company_item_rst.id,
                        'value': employee.company_id.name or "McDonald's Digital",
                    })
                if name_item_rst:
                    v_create.append({
                        'sign_request_item_id': item.id,
                        'sign_item_id': name_item_rst.id,
                        'value': employee.name,
                    })
                
                if v_create:
                    self.env['sign.request.item.value'].sudo().create(v_create)
                
                # 2. Lưu ID tham chiếu (chỉ khi module 0212 đã cài)
                if 'x_psm_0212_handover_sign_request_id' in employee._fields:
                    employee.sudo().x_psm_0212_handover_sign_request_id = item.sign_request_id.id

    def write(self, vals):
        # Giữ lại ghi đè write trên item để bắt kịp các sự kiện lẻ (nếu cần), 
        # nhưng logic chính đã chuyển lên SignRequest
        return super().write(vals)
