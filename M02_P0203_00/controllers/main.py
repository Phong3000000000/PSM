import base64
from odoo import http
from odoo.http import request

class PortalInfoUpdate(http.Controller):

    @http.route(['/my/update_info'], type='http', auth="user", website=True)
    def portal_my_update_info(self, **kw):
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not employee:
            employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)
        countries = request.env['res.country'].sudo().search([])
        # Lấy danh sách user nội bộ HOẶC Portal Manager để chọn quản lý duyệt
        users = request.env['res.users'].sudo().search(['|', ('share', '=', False), ('x_is_portal_manager', '=', True)])
        states = request.env['res.country.state'].sudo().search([])

        # Get document completion status (safely)
        doc_status = {}
        if hasattr(partner, 'get_portal_documents_status'):
            doc_status = partner.get_portal_documents_status()

        bank_accounts = request.env['res.partner.bank'].sudo().search([('partner_id', '=', partner.id)])
        banks = request.env['res.bank'].sudo().search([])

        return request.render("M02_P0203_00.request_portal_templates", {
            'partner': partner,
            'employee': employee,
            'countries': countries,
            'states': states,
            'users': users,
            'doc_status': doc_status,
            'bank_accounts': bank_accounts,
            'banks': banks,
        })

    @http.route(['/my/update_info/submit'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_my_update_info_submit(self, **post):
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not employee:
            employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)

        category = request.env.ref('M02_P0203_00.approval_category_contact_update').sudo()

        # Xử lý file upload sang định dạng base64
        work_permit_file = post.get('has_work_permit')

        # Đồng bộ company_id của partner với employee để tránh lỗi company crossover
        if employee and employee.company_id and partner.company_id != employee.company_id:
            partner.sudo().write({'company_id': employee.company_id.id})

        vals = {
            'name': f"Yêu cầu cập nhật từ {partner.name}",
            'category_id': category.id,
            'partner_id': partner.id,
            'company_id': employee.company_id.id if employee and employee.company_id else False,

            # 1. Private Contact
            'private_email': post.get('private_email'),
            'private_phone': post.get('private_phone'),
            'acc_number': post.get('acc_number'),
            'bank_id': int(post.get('bank_id')) if post.get('bank_id') else False,

            # 2. Personal Information
            'legal_name': post.get('legal_name'),
            'birthday': post.get('birthday'),
            'place_of_birth': post.get('place_of_birth'),
            'country_of_birth': int(post.get('country_of_birth')) if post.get('country_of_birth') else False,
            'sex': post.get('sex'),

            # 3. Emergency Contact
            'emergency_contact': post.get('emergency_contact'),
            'emergency_phone': post.get('emergency_phone'),

            # 4. Visa & Work Permit
            'visa_no': post.get('visa_no'),
            'visa_expire': post.get('visa_expire'),
            'permit_no': post.get('permit_no'),
            'work_permit_expiration_date': post.get('work_permit_expiration_date'),

            # 5. Citizenship
            'country_id': int(post.get('country_id')) if post.get('country_id') else False,
            'identification_id': post.get('identification_id'),
            'ssnid': post.get('ssnid'),
            'passport_id': post.get('passport_id'),
            'passport_expiration_date': post.get('passport_expiration_date'),

            # 6. Location
            'private_street': post.get('private_street'),
            'private_street2': post.get('private_street2'),
            'private_city': post.get('private_city'),
            'private_state_id': int(post.get('private_state_id')) if post.get('private_state_id') else False,
            'private_zip': post.get('private_zip'),
            'private_country_id': int(post.get('private_country_id')) if post.get('private_country_id') else False,
            'distance_home_work': float(post.get('distance_home_work')) if post.get('distance_home_work') else 0.0,
            'distance_home_work_unit': post.get('distance_home_work_unit'),

            # 7. Family
            'marital': post.get('marital'),
            'children': int(post.get('children')) if post.get('children') else 0,
            'spouse_complete_name': post.get('spouse_complete_name'),
            'spouse_birthdate': post.get('spouse_birthdate'),

            # 8. Education
            'certificate': post.get('certificate'),
            'study_field': post.get('study_field'),
            'study_school': post.get('study_school'),
        }

        # Tự động lấy quản lý trực tiếp
        approver_user_id = False

        if employee and employee.parent_id:
            parent = employee.parent_id
            if parent.user_id:
                approver_user_id = parent.user_id.id
            else:
                # Multi-company fallback: tìm user qua work_contact_id (partner)
                if parent.work_contact_id:
                    fallback_user = request.env['res.users'].sudo().search([
                        ('partner_id', '=', parent.work_contact_id.id)
                    ], limit=1)
                    if fallback_user:
                        approver_user_id = fallback_user.id

        if approver_user_id:
            vals['approver_ids'] = [(0, 0, {
                'user_id': approver_user_id,
                'status': 'new',
                'required': True,
            })]

        if work_permit_file:
            vals['has_work_permit'] = base64.b64encode(work_permit_file.read())

        # Tạo record trong approval.request
        approval_request = request.env['approval.request'].sudo().create(vals)

        # Create attachments
        attachments = request.httprequest.files.getlist('attachment_ids')
        for attachment in attachments:
            if attachment:
                request.env['ir.attachment'].sudo().create({
                    'name': attachment.filename,
                    'datas': base64.b64encode(attachment.read()),
                    'res_model': 'approval.request',
                    'res_id': approval_request.id,
                    'type': 'binary',
                })

        # Tự động confirm để chuyển sang trạng thái Submitted (pending)
        approval_request.action_confirm()

        return request.redirect('/my?success=1')

    @http.route(['/my/contact/update'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_my_contact_update(self, **post):
        partner = request.env.user.partner_id
        vals = {}
        file_fields = [
            'passport_photo', 'id_card_front', 'id_card_back',
            'household_registration', 'judicial_record',
            'professional_certificate', 'additional_certificates'
        ]
        for field in file_fields:
            file = post.get(field)
            if file and hasattr(file, 'read'):
                file_content = file.read()
                vals[field] = base64.b64encode(file_content)
                vals[f'{field}_filename'] = file.filename
        if vals:
            partner.sudo().write(vals)
        return request.redirect('/my/update_info#onboard')
