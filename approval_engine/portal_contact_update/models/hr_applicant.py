from odoo import models, fields, api

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # ========== DOCUMENT APPROVAL STATUS ==========
    document_approval_status = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Không duyệt')
    ], string="Trạng thái hồ sơ", default='pending', tracking=True)

    # ========== RELATED FIELDS (SYNC WITH PARTNER) ==========
    
    # 1. Ảnh thẻ
    passport_photo = fields.Binary(related='partner_id.passport_photo', readonly=False, string="Ảnh thẻ")
    passport_photo_filename = fields.Char(related='partner_id.passport_photo_filename', readonly=False)

    # 2. CCCD/CMND
    id_card_front = fields.Binary(related='partner_id.id_card_front', readonly=False, string="CCCD - Mặt trước")
    id_card_front_filename = fields.Char(related='partner_id.id_card_front_filename', readonly=False)
    
    id_card_back = fields.Binary(related='partner_id.id_card_back', readonly=False, string="CCCD - Mặt sau")
    id_card_back_filename = fields.Char(related='partner_id.id_card_back_filename', readonly=False)

    # 3. Hộ khẩu
    household_registration = fields.Binary(related='partner_id.household_registration', readonly=False, string="Sổ hộ khẩu")
    household_registration_filename = fields.Char(related='partner_id.household_registration_filename', readonly=False)

    # 4. Lý lịch tư pháp
    judicial_record = fields.Binary(related='partner_id.judicial_record', readonly=False, string="Lý lịch tư pháp")
    judicial_record_filename = fields.Char(related='partner_id.judicial_record_filename', readonly=False)

    # 5. Bằng cấp
    professional_certificate = fields.Binary(related='partner_id.professional_certificate', readonly=False, string="Bằng cấp chuyên môn")
    professional_certificate_filename = fields.Char(related='partner_id.professional_certificate_filename', readonly=False)
    
    additional_certificates = fields.Binary(related='partner_id.additional_certificates', readonly=False, string="Chứng chỉ khác")
    additional_certificates_filename = fields.Char(related='partner_id.additional_certificates_filename', readonly=False)
    
    # Tracking info
    portal_last_update = fields.Datetime(related='partner_id.portal_last_update', readonly=True, string="Cập nhật lần cuối")
    portal_updates_count = fields.Integer(related='partner_id.portal_updates_count', readonly=True, string="Số lần cập nhật")

    # ========== ACTIONS ==========
    def action_approve_documents(self):
        # Find 'Contract Signed' stage (search case insensitive)
        stage = self.env['hr.recruitment.stage'].search([('name', 'ilike', 'Contract Signed')], limit=1)
        
        for rec in self:
            rec.document_approval_status = 'approved'
            if stage:
                rec.stage_id = stage.id
                rec.message_post(body="✅ Hồ sơ đã được duyệt! Đã chuyển sang trạng thái 'Contract Signed'.")
            else:
                rec.message_post(body="✅ Hồ sơ đã được duyệt! (Không tìm thấy stage 'Contract Signed')")

    def action_refuse_documents(self):
        for rec in self:
            rec.document_approval_status = 'refused'
            # Optional: Move to Refused stage if exists? User didn't ask, just ribbon.
            rec.message_post(body="❌ Hồ sơ KHÔNG được duyệt.")
