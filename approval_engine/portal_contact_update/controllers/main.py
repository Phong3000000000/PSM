import base64
from odoo import http
from odoo.http import request

class PortalInfoUpdate(http.Controller):

    @http.route(['/my/update_info'], type='http', auth="user", website=True)
    def portal_my_update_info(self, **kw):
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)
        countries = request.env['res.country'].sudo().search([])
        # Lấy danh sách user nội bộ để chọn quản lý duyệt
        users = request.env['res.users'].sudo().search([('share', '=', False)])
        states = request.env['res.country.state'].sudo().search([])
        
        return request.render("portal_contact_update.request_portal_templates", {
            'partner': partner,
            'employee': employee,
            'countries': countries,
            'states': states,
            'users': users,
        })

    @http.route(['/my/update_info/submit'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_my_update_info_submit(self, **post):
        partner = request.env.user.partner_id
        category = request.env.ref('portal_contact_update.approval_category_contact_update')

        # Xử lý file upload sang định dạng base64
        passport_file = post.get('passport_photo')
        id_front_file = post.get('id_card_front')
        work_permit_file = post.get('has_work_permit')

        vals = {
            'name': f"Yêu cầu cập nhật từ {partner.name}",
            'category_id': category.id,
            'partner_id': partner.id,
            # 'request_status': 'pending',  <-- Remove this, let action_confirm handle it
            
            # Basic Info
            'new_name': post.get('new_name'),
            'new_phone': post.get('new_phone'),
            'sex': post.get('sex'),
            'birthday': post.get('birthday'),
            
            # 1. Private Contact
            'private_email': post.get('private_email'),
            'private_phone': post.get('private_phone'),
            'legal_name': post.get('legal_name'),

            # 2. Birth
            'place_of_birth': post.get('place_of_birth'),
            'country_of_birth': int(post.get('country_of_birth')) if post.get('country_of_birth') else False,

            # 3. Visa & Work Permit
            'visa_no': post.get('visa_no'),
            'visa_expire': post.get('visa_expire'),
            'permit_no': post.get('permit_no'),
            'work_permit_expiration_date': post.get('work_permit_expiration_date'),
            
            # 4. Citizenship
            'country_id': int(post.get('country_id')) if post.get('country_id') else False,
            'identification_id': post.get('identification_id'),
            'passport_id': post.get('passport_id'),
            'ssnid': post.get('ssnid'),
            'passport_expiration_date': post.get('passport_expiration_date'),
            
            # 5. Address (Private)
            'private_street': post.get('private_street'),
            'private_street2': post.get('private_street2'),
            'private_city': post.get('private_city'),
            'private_state_id': int(post.get('private_state_id')) if post.get('private_state_id') else False,
            'private_zip': post.get('private_zip'),
            'private_country_id': int(post.get('private_country_id')) if post.get('private_country_id') else False,
            'distance_home_work': int(post.get('distance_home_work')) if post.get('distance_home_work') else 0,

            # 6. Family
            'marital': post.get('marital'),
            'children': int(post.get('children')) if post.get('children') else 0,
            'spouse_complete_name': post.get('spouse_complete_name'),
            'spouse_birthdate': post.get('spouse_birthdate'),
            
            # Emergency
            'emergency_contact': post.get('emergency_contact'),
            'emergency_phone': post.get('emergency_phone'),
            
            # Education
            'certificate': post.get('certificate'),
            'study_field': post.get('study_field'),
            'study_school': post.get('study_school'),
        }

        # Nếu user chọn người duyệt
        if post.get('approver_user_id'):
            vals['approver_ids'] = [(0, 0, {
                'user_id': int(post.get('approver_user_id')),
                'status': 'new',
                'required': True,
            })]

        if passport_file:
            vals['passport_photo'] = base64.b64encode(passport_file.read())
        if id_front_file:
            vals['id_card_front'] = base64.b64encode(id_front_file.read())
        if work_permit_file:
            vals['has_work_permit'] = base64.b64encode(work_permit_file.read())

        # Tạo record trong approval.request
        approval_request = request.env['approval.request'].sudo().create(vals)
        
        # Tự động confirm để chuyển sang trạng thái Submitted (pending)
        approval_request.action_confirm()

        return request.redirect('/my?success=1')