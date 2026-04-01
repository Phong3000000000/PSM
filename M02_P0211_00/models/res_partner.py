from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ========== PERSONAL DOCUMENT FIELDS ==========
    
    # 1. Ảnh thẻ (Passport Photo)
    passport_photo = fields.Binary(string="Ảnh thẻ", attachment=True)
    passport_photo_filename = fields.Char(string="Tên file Ảnh thẻ")
    
    # 2. CCCD/CMND (Citizen ID)
    id_card_front = fields.Binary(string="CCCD - Mặt trước", attachment=True)
    id_card_front_filename = fields.Char(string="Tên file CCCD trước")
    
    id_card_back = fields.Binary(string="CCCD - Mặt sau", attachment=True)
    id_card_back_filename = fields.Char(string="Tên file CCCD sau")
    
    # 3. Hộ khẩu bản sao (Household Registration)
    household_registration = fields.Binary(string="Sổ hộ khẩu", attachment=True)
    household_registration_filename = fields.Char(string="Tên file Sổ hộ khẩu")
    
    # 4. Lý lịch tư pháp (Judicial Record)
    judicial_record = fields.Binary(string="Lý lịch tư pháp", attachment=True)
    judicial_record_filename = fields.Char(string="Tên file Lý lịch tư pháp")
    
    # 5. Bằng cấp chuyên môn (Professional Certificates)
    professional_certificate = fields.Binary(string="Bằng cấp chuyên môn", attachment=True)
    professional_certificate_filename = fields.Char(string="Tên file Bằng cấp")
    
    # Additional professional certificates (multiple)
    additional_certificates = fields.Binary(string="Chứng chỉ khác", attachment=True)
    additional_certificates_filename = fields.Char(string="Tên file Chứng chỉ khác")
    
    # ========== PORTAL TRACKING ==========
    
    portal_last_update = fields.Datetime(string="Cập nhật lần cuối")
    portal_updates_count = fields.Integer(string="Số lần cập nhật", default=0)
    
    # Computed field cho portal URL
    portal_url = fields.Char(
        string="Portal URL",
        compute="_compute_portal_url",
        store=False
    )
    
    @api.depends('email')
    def _compute_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for partner in self:
            if partner.email:
                partner.portal_url = f"{base_url}/my/contact"
            else:
                partner.portal_url = False
    
    # ========== HELPER METHODS ==========
    
    def get_portal_documents_status(self):
        """Return document completion status"""
        docs = [
            ('passport_photo', 'Passport Photo'),
            ('id_card_front', 'ID Card Front'),
            ('id_card_back', 'ID Card Back'),
            ('household_registration', 'Household Registration'),
            ('judicial_record', 'Judicial Record'),
            ('professional_certificate', 'Professional Certificate'),
        ]
        
        completed = []
        pending = []
        
        for field_name, doc_name in docs:
            if getattr(self, field_name):
                completed.append(doc_name)
            else:
                pending.append(doc_name)
        
        return {
            'completed': completed,
            'pending': pending,
            'completion_rate': len(completed) / len(docs) * 100 if docs else 0
        }
    
    # Override write để tracking portal updates
    def write(self, vals):
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("res_partner.write() called")
        _logger.info(f"   Updating {len(self)} partner(s)")
        _logger.info(f"   Values keys: {list(vals.keys())}")
        
        # Kiểm tra nếu có update từ portal
        portal_fields = [
            'passport_photo', 'id_card_front', 'id_card_back',
            'household_registration', 'judicial_record', 
            'professional_certificate', 'additional_certificates'
        ]
        
        # Log document fields
        for field in portal_fields:
            if field in vals:
                if vals[field]:
                    _logger.info(f"   {field}: Binary data present")
                filename_field = f"{field}_filename"
                if filename_field in vals:
                    _logger.info(f"   {filename_field}: {vals[filename_field]}")
        
        # Auto-add filename if binary data present but filename missing
        file_mappings = {
            'passport_photo': 'passport_photo_filename',
            'id_card_front': 'id_card_front_filename',
            'id_card_back': 'id_card_back_filename',
            'household_registration': 'household_registration_filename',
            'judicial_record': 'judicial_record_filename',
            'professional_certificate': 'professional_certificate_filename',
            'additional_certificates': 'additional_certificates_filename',
        }
        
        for binary_field, filename_field in file_mappings.items():
            if binary_field in vals and vals[binary_field] and filename_field not in vals:
                vals[filename_field] = f"{binary_field}.upload"
                _logger.info(f"   Auto-added {filename_field}")
        
        if any(field in vals for field in portal_fields):
            vals['portal_last_update'] = fields.Datetime.now()
            vals['portal_updates_count'] = (self.portal_updates_count or 0) + 1
            _logger.info(f"   Portal tracking updated: count = {vals['portal_updates_count']}")
            
            # Log activity
            updated_docs = [f for f in portal_fields if f in vals]
            if updated_docs:
                self.message_post(
                    body=f"Contact updated documents via portal: {', '.join(updated_docs)}",
                    subject="Portal Documents Updated"
                )
        
        result = super(ResPartner, self).write(vals)
        _logger.info(f"   Write completed successfully")
        return result