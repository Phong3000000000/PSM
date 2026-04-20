from odoo import models, fields, api

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # ========== DOCUMENT APPROVAL STATUS ==========
    x_psm_0211_document_approval_status = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Không duyệt')
    ], string="Trạng thái hồ sơ", default='pending', tracking=True)

    # ========== RELATED FIELDS (SYNC WITH PARTNER) ==========
    
    # 1. Ảnh thẻ
    x_psm_0211_passport_photo = fields.Binary(related='partner_id.x_psm_0211_passport_photo', readonly=False, string="Ảnh thẻ")
    x_psm_0211_passport_photo_filename = fields.Char(related='partner_id.x_psm_0211_passport_photo_filename', readonly=False)

    # 2. CCCD/CMND
    x_psm_0211_id_card_front = fields.Binary(related='partner_id.x_psm_0211_id_card_front', readonly=False, string="CCCD - Mặt trước")
    x_psm_0211_id_card_front_filename = fields.Char(related='partner_id.x_psm_0211_id_card_front_filename', readonly=False)
    
    x_psm_0211_id_card_back = fields.Binary(related='partner_id.x_psm_0211_id_card_back', readonly=False, string="CCCD - Mặt sau")
    x_psm_0211_id_card_back_filename = fields.Char(related='partner_id.x_psm_0211_id_card_back_filename', readonly=False)

    # 3. Hộ khẩu
    x_psm_0211_household_registration = fields.Binary(related='partner_id.x_psm_0211_household_registration', readonly=False, string="Sổ hộ khẩu")
    x_psm_0211_household_registration_filename = fields.Char(related='partner_id.x_psm_0211_household_registration_filename', readonly=False)

    # 4. Lý lịch tư pháp
    x_psm_0211_judicial_record = fields.Binary(related='partner_id.x_psm_0211_judicial_record', readonly=False, string="Lý lịch tư pháp")
    x_psm_0211_judicial_record_filename = fields.Char(related='partner_id.x_psm_0211_judicial_record_filename', readonly=False)

    # 5. Bằng cấp
    x_psm_0211_professional_certificate = fields.Binary(related='partner_id.x_psm_0211_professional_certificate', readonly=False, string="Bằng cấp chuyên môn")
    x_psm_0211_professional_certificate_filename = fields.Char(related='partner_id.x_psm_0211_professional_certificate_filename', readonly=False)
    
    x_psm_0211_additional_certificates = fields.Binary(related='partner_id.x_psm_0211_additional_certificates', readonly=False, string="Chứng chỉ khác")
    x_psm_0211_additional_certificates_filename = fields.Char(related='partner_id.x_psm_0211_additional_certificates_filename', readonly=False)
    
    # Tracking info
    x_psm_0211_portal_last_update = fields.Datetime(related='partner_id.x_psm_0211_portal_last_update', readonly=True, string="Cập nhật lần cuối")
    x_psm_0211_portal_updates_count = fields.Integer(related='partner_id.x_psm_0211_portal_updates_count', readonly=True, string="Số lần cập nhật")

    # ========== ACTIONS ==========
    def action_psm_approve_documents(self):
        # Find 'Contract Signed' stage (search case insensitive)
        stage = self.env['hr.recruitment.stage'].search([('name', 'ilike', 'Contract Signed')], limit=1)
        
        for rec in self:
            rec.x_psm_0211_document_approval_status = 'approved'
            if stage:
                rec.stage_id = stage.id
                from markupsafe import Markup as markup
                rec.message_post(body=markup("Hồ sơ đã được duyệt! Đã chuyển sang trạng thái <b>'Contract Signed'</b>."))
            else:
                from markupsafe import Markup as markup
                rec.message_post(body=markup("Hồ sơ đã được duyệt! (Không tìm thấy stage 'Contract Signed')"))

    def action_psm_reject_documents(self):
        for rec in self:
            rec.x_psm_0211_document_approval_status = 'refused'
            # Optional: Move to Refused stage if exists? User didn't ask, just ribbon.
            from markupsafe import Markup as markup
            rec.message_post(body=markup("Hồ sơ KHÔNG được duyệt."))
