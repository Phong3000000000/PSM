from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Gỡ bỏ các ràng buộc bảo mật trường để PM/BP không bị lỗi Access Error khi xử lý portal/onboarding
    # PHẢI GIỮ company_dependent=True nếu không sẽ lỗi hệ thống kế toán
    credit_limit = fields.Float(groups=False, company_dependent=True)
    signup_token = fields.Char(groups=False)
    signup_type = fields.Char(groups=False)
    signup_expiration = fields.Datetime(groups=False)


    # ========== PERSONAL DOCUMENT FIELDS ==========
    
    # 1. Ảnh thẻ (Passport Photo)
    x_psm_0211_passport_photo = fields.Binary(string="Ảnh thẻ", attachment=True)
    x_psm_0211_passport_photo_filename = fields.Char(string="Tên file Ảnh thẻ")
    
    # 2. Identity Documents (CCCD / Identifier)
    x_psm_0211_id_card = fields.Binary(string="Identity Card", attachment=True)
    x_psm_0211_id_card_filename = fields.Char(string="Identity Card Filename")
    
    x_psm_0211_id_card_front = fields.Binary(string="CCCD - Mặt trước", attachment=True)
    x_psm_0211_id_card_front_filename = fields.Char(string="Tên file CCCD trước")
    
    x_psm_0211_id_card_back = fields.Binary(string="CCCD - Mặt sau", attachment=True)
    x_psm_0211_id_card_back_filename = fields.Char(string="Tên file CCCD sau")
    
    # 3. Personal History Group (Sơ yếu lý lịch / CT07 / SHK)
    x_psm_0211_curriculum_vitae = fields.Binary(string="Personal History", attachment=True)
    x_psm_0211_curriculum_vitae_filename = fields.Char(string="Personal History Filename")

    x_psm_0211_household_registration = fields.Binary(string="Sổ hộ khẩu", attachment=True)
    x_psm_0211_household_registration_filename = fields.Char(string="Tên file Sổ hộ khẩu")
    
    # 4. Health & Insurance
    x_psm_0211_health_certificate = fields.Binary(string="Health Certificate (TT32)", attachment=True)
    x_psm_0211_health_certificate_filename = fields.Char(string="Health Certificate Filename")

    x_psm_0211_social_insurance = fields.Binary(string="Social Insurance (BHXH)", attachment=True)
    x_psm_0211_social_insurance_filename = fields.Char(string="Social Insurance Filename")

    # 5. Others
    x_psm_0211_driving_license = fields.Binary(string="Driving License", attachment=True)
    x_psm_0211_driving_license_filename = fields.Char(string="Driving License Filename")

    x_psm_0211_judicial_record = fields.Binary(string="Lý lịch tư pháp", attachment=True)
    x_psm_0211_judicial_record_filename = fields.Char(string="Tên file Lý lịch tư pháp")
    
    x_psm_0211_professional_certificate = fields.Binary(string="Professional Certificate", attachment=True)
    x_psm_0211_professional_certificate_filename = fields.Char(string="Professional Certificate Filename")
    
    x_psm_0211_additional_certificates = fields.Binary(string="Other Certificates", attachment=True)
    x_psm_0211_additional_certificates_filename = fields.Char(string="Other Certificates Filename")
    
    # ========== PORTAL TRACKING ==========
    
    x_psm_0211_portal_last_update = fields.Datetime(string="Last Portal Update")
    x_psm_0211_portal_updates_count = fields.Integer(string="Field Update Count", default=0)
    x_psm_portal_revision_count = fields.Integer(string="Submission Count", default=0)
    x_psm_0211_portal_submitted = fields.Boolean(string="Portal Submitted", default=False)
    
    # Computed field cho portal URL
    x_psm_0211_portal_url = fields.Char(
        string="Portal URL",
        compute="_compute_psm_0211_portal_url",
        store=False
    )
    
    @api.depends('email')
    def _compute_psm_0211_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for partner in self:
            if partner.email:
                partner.x_psm_0211_portal_url = f"{base_url}/my/onboard_info"
            else:
                partner.x_psm_0211_portal_url = False
    
    # ========== HELPER METHODS ==========
    
    def get_psm_0211_portal_documents_status(self):
        """Return document completion status"""
        docs = [
            ('x_psm_0211_id_card', 'Identity Card'),
            ('x_psm_0211_curriculum_vitae', 'Personal History / CV'),
            ('x_psm_0211_health_certificate', 'Health Certificate'),
        ]
        
        # Additional for FT info display logic in portal can use this or controller
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
            'pending_count': len(pending),
            'completion_rate': len(completed) / len(docs) * 100 if docs else 0
        }
    
    # Override write để tracking portal updates
    def write(self, vals):
        # Auto-add filename if binary data present but filename missing
        file_mappings = {
            'x_psm_0211_id_card': 'x_psm_0211_id_card_filename',
            'x_psm_0211_curriculum_vitae': 'x_psm_0211_curriculum_vitae_filename',
            'x_psm_0211_health_certificate': 'x_psm_0211_health_certificate_filename',
            'x_psm_0211_social_insurance': 'x_psm_0211_social_insurance_filename',
            'x_psm_0211_driving_license': 'x_psm_0211_driving_license_filename',
            'x_psm_0211_passport_photo': 'x_psm_0211_passport_photo_filename',
            'x_psm_0211_judicial_record': 'x_psm_0211_judicial_record_filename',
            'x_psm_0211_professional_certificate': 'x_psm_0211_professional_certificate_filename',
            'x_psm_0211_additional_certificates': 'x_psm_0211_additional_certificates_filename',
        }
        
        for binary_field, filename_field in file_mappings.items():
            if binary_field in vals and vals[binary_field] and filename_field not in vals:
                vals[filename_field] = f"{binary_field}.upload"
        
        portal_fields = list(file_mappings.keys())
        if any(field in vals for field in portal_fields):
            vals['x_psm_0211_portal_last_update'] = fields.Datetime.now()
            vals['x_psm_0211_portal_updates_count'] = (self.x_psm_0211_portal_updates_count or 0) + 1
            
            # Log activity to chatter
            updated_docs = [f for f in portal_fields if f in vals]
            if updated_docs:
                from markupsafe import Markup as markup
                self.message_post(
                    body=markup(f"Contact updated documents via portal: {', '.join(updated_docs)}"),
                    subject="Portal Documents Updated"
                )
        
        return super().write(vals)
