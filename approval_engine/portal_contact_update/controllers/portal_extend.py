# -*- coding: utf-8 -*-
import base64
import logging
from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request

_logger = logging.getLogger(__name__)

class CustomerPortalCustom(CustomerPortal):

    CUSTOM_FIELDS = [
        "passport_photo",
        "passport_photo_filename",
        "id_card_front",
        "id_card_front_filename",
        "id_card_back",
        "id_card_back_filename",
        "household_registration",
        "household_registration_filename",
        "judicial_record",
        "judicial_record_filename",
        "professional_certificate",
        "professional_certificate_filename",
        "additional_certificates",
        "additional_certificates_filename",
    ]

    # 🔥 THÊM METHOD account() VỚI LOGGING
    @http.route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        """Override để đảm bảo controller được gọi"""
        _logger.info("=" * 80)
        _logger.info("🚀 [START] CUSTOM account() METHOD CALLED")
        _logger.info(f"📧 Request method: {request.httprequest.method}")
        _logger.info(f"🔑 POST keys: {list(post.keys())}")
        _logger.info(f"📁 Request files: {list(request.httprequest.files.keys())}")
        
        # DEBUG: Log tất cả data từ form
        for key, value in post.items():
            if isinstance(value, str) and len(value) < 100:
                _logger.info(f"   📝 {key} = '{value}'")
        
        # Xử lý file upload trực tiếp từ request
        if request.httprequest.method == 'POST' and request.httprequest.files:
            _logger.info("📎 Processing uploaded files...")
            for field_name, file_obj in request.httprequest.files.items():
                if hasattr(file_obj, 'filename') and file_obj.filename:
                    _logger.info(f"   📄 {field_name}: {file_obj.filename}")
                    # Đọc và chuyển thành base64
                    try:
                        content = file_obj.read()
                        if content:
                            post[field_name] = base64.b64encode(content).decode('utf-8')
                            
                            # Thêm filename field
                            post[f"{field_name}_filename"] = file_obj.filename
                                
                            _logger.info(f"   ✅ Processed {field_name} ({len(content)} bytes)")
                    except Exception as e:
                        _logger.error(f"   ❌ Error processing {field_name}: {e}")
        
        _logger.info("🔄 Calling parent account()...")
        result = super().account(redirect=redirect, **post)
        _logger.info("🏁 [END] Parent account() returned")
        _logger.info("=" * 80)
        return result

    def _get_optional_fields(self):
        """Thêm custom fields vào danh sách optional fields"""
        base_fields = super()._get_optional_fields()
        _logger.info(f"📋 _get_optional_fields: {len(base_fields)} base fields")
        _logger.info(f"   Adding custom fields: {self.CUSTOM_FIELDS}")
        return base_fields + self.CUSTOM_FIELDS

    def _handle_file_upload(self, data):
        """
        Xử lý file upload từ form portal
        """
        _logger.info("🔄 _handle_file_upload called")
        _logger.info(f"   Input keys: {list(data.keys())}")
        
        # Xử lý file upload
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
            if binary_field in data and isinstance(data[binary_field], str) and data[binary_field]:
                # Nếu đã là base64 string từ account() method
                _logger.info(f"   ✅ {binary_field}: Already base64 encoded")
                if filename_field not in data:
                    data[filename_field] = f"{binary_field}.upload"
            elif binary_field in data and hasattr(data[binary_field], 'read'):
                # Nếu là file object
                file_obj = data[binary_field]
                content = file_obj.read()
                if content:
                    data[binary_field] = base64.b64encode(content)
                    data[filename_field] = getattr(file_obj, 'filename', f'{binary_field}.upload')
                    _logger.info(f"   ✅ Processed {binary_field} file")
                else:
                    data.pop(binary_field, None)
        
        return data

    def _handle_address_form(self, partner, data):
        """
        Override handler để xử lý custom fields
        """
        _logger.info("💾 _handle_address_form START")
        _logger.info(f"   Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"   Data keys: {list(data.keys())}")
        
        # Log custom fields trước khi xử lý
        custom_fields = ['bank_name', 'bank_account_number', 'cccd_front', 'cccd_front_filename']
        for field in custom_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    _logger.info(f"   📍 {field} = '{value[:50]}{'...' if len(value) > 50 else ''}'")
        
        # Xử lý file upload
        data = self._handle_file_upload(data)
        
        _logger.info("🔄 Calling parent _handle_address_form...")
        result = super()._handle_address_form(partner, data)
        _logger.info(f"   Parent returned: {result}")
        
        # Kiểm tra sau khi save
        partner.refresh()
        _logger.info("✅ AFTER SAVE CHECK:")
        _logger.info(f"   bank_name: {partner.bank_name or '(empty)'}")
        _logger.info(f"   cccd_front: {'✅ HAS DATA' if partner.cccd_front else '❌ EMPTY'}")
        _logger.info(f"   cccd_front_filename: {partner.cccd_front_filename or '(empty)'}")
        
        _logger.info("🏁 _handle_address_form END")
        return result