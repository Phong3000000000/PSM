from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64
import logging

_logger = logging.getLogger(__name__)

DOCUMENT_FIELDS = [
    'x_psm_0211_id_card_front',
    'x_psm_0211_id_card_back',
    'x_psm_0211_curriculum_vitae',
    'x_psm_0211_health_certificate',
    'x_psm_0211_social_insurance',
    'x_psm_0211_driving_license',
    'x_psm_0211_passport_photo',
    'x_psm_0211_judicial_record',
    'x_psm_0211_professional_certificate',
    'x_psm_0211_additional_certificates',
]


class PortalContactController(CustomerPortal):

    def _get_employee_for_portal_user(self):
        """Find hr.employee linked to current portal user."""
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search(
            [('work_contact_id', '=', partner.id)], limit=1
        )
        if not employee:
            email = request.env.user.email
            if email:
                employee = request.env['hr.employee'].sudo().search(
                    ['|', ('work_email', '=', email),
                          ('private_email', '=', email)], limit=1, order="id desc"
                )
        return employee

    def home(self, **kw):
        """Redirect onboarding candidates to their upload page with safety checks."""
        try:
            user = request.env.user
            if user.has_group('base.group_portal'):
                employee = self._get_employee_for_portal_user()
                # Check for field existence in DB to avoid 500 during upgrade
                if employee:
                    state = employee.x_psm_0211_onboarding_state
                    if state == 'pending':
                        return request.redirect('/my/onboard_info')
        except Exception:
            _logger.warning("Portal Home: Fail-safe triggered (likely missing DB columns during upgrade).")
            
        return super().home(**kw)

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        """If logged in as a candidate, direct to upload page with safety checks."""
        if request.session.uid:
            try:
                user = request.env.user
                if user.has_group('base.group_portal'):
                    employee = self._get_employee_for_portal_user()
                    if employee and employee.x_psm_0211_onboarding_state == 'pending':
                        return request.redirect('/my/onboard_info')
            except Exception:
                pass 
        
        # Fallback to standard Odoo behavior
        return request.redirect('/my')

    @http.route('/my/onboard_info', type='http', auth='user', website=True)
    def portal_contact_page(self, **post):
        """Main portal page for document upload."""
        employee = self._get_employee_for_portal_user()
        contract_type = post.get('contract_type')

        doc_status = {'completed': [], 'pending': [], 'pending_count': 0, 'completion_rate': 0}
        doc_is_image = {}

        if employee:
            if employee.contract_type_id:
                ctype_name = (employee.contract_type_id.name or '').lower()
                contract_type = 'fulltime' if 'full' in ctype_name else 'parttime'
            
            if not contract_type:
                contract_type = post.get('contract_type')

            # REQUIRED FIELDS depending on FT/PT
            required_fields = ['x_psm_0211_id_card_front', 'x_psm_0211_id_card_back', 'x_psm_0211_curriculum_vitae', 'x_psm_0211_health_certificate']
            if contract_type == 'fulltime':
                required_fields.append('x_psm_0211_passport_photo')

            # Check document status
            _img_exts = ('.png', '.jpg', '.jpeg', '.webp')
            completed = []
            pending = []

            for f in required_fields:
                if getattr(employee, f):
                    completed.append(f)
                else:
                    pending.append(f)

            doc_status = {
                'completed': completed,
                'pending': pending,
                'pending_count': len(pending),
                'completion_rate': len(completed) / len(required_fields) * 100 if required_fields else 0,
            }

            doc_is_image = {
                f: bool(
                    getattr(employee, f'{f}_filename', '') and
                    getattr(employee, f'{f}_filename', '').lower().endswith(_img_exts)
                )
                for f in DOCUMENT_FIELDS
            }

            # Lazy sync: nếu đã có file nhưng state vẫn pending → cập nhật
            has_any_file = any(getattr(employee, f) for f in DOCUMENT_FIELDS)
            if has_any_file and employee.x_psm_0211_onboarding_state == 'pending':
                employee.sudo().write({'x_psm_0211_onboarding_state': 'submitted'})

            # NẾU 100% tài liệu đã đủ nhưng chưa chốt, tự động khóa luôn
            if doc_status['pending_count'] == 0 and not request.env.user.partner_id.x_psm_0211_portal_submitted:
                request.env.user.partner_id.sudo().write({'x_psm_0211_portal_submitted': True})

        return request.render('M02_P0211.portal_contact_form', {
            'partner': request.env.user.partner_id,
            'employee': employee,
            'doc_status': doc_status,
            'doc_is_image': doc_is_image,
            'success': post.get('success', False),
            'contract_type': contract_type,
        })

    @http.route('/my/onboard_info/submit', type='http', auth='user', website=True,
                csrf=True, methods=['POST'])
    def onboard_info_submit(self, **post):
        """Xử lý form upload tài liệu từ portal."""
        employee = self._get_employee_for_portal_user()

        if not employee:
            _logger.warning("Portal upload: hr.employee not found for user %s", request.env.user.login)
            return request.redirect('/my/onboard_info?error=no_employee')


        try:
            update_vals = {}

            for field in DOCUMENT_FIELDS:
                if field in request.httprequest.files:
                    uploaded_file = request.httprequest.files[field]
                    if uploaded_file and uploaded_file.filename:
                        update_vals[field] = base64.b64encode(uploaded_file.read())
                        update_vals[f'{field}_filename'] = uploaded_file.filename

            if update_vals:
                import odoo.fields as ofields
                update_vals['x_psm_0211_portal_last_update'] = ofields.Datetime.now()
                # Update field update count
                update_vals['x_psm_0211_portal_updates_count'] = (employee.x_psm_0211_portal_updates_count or 0) + 1
                # Update rounds of submission
                update_vals['x_psm_portal_revision_count'] = (employee.x_psm_portal_revision_count or 0) + 1
                
                employee.sudo().write(update_vals)

                # Sync to partner
                partner_vals = {
                    k: v for k, v in update_vals.items() 
                    if k in request.env.user.partner_id._fields
                }
                if partner_vals:
                    request.env.user.partner_id.sudo().write(partner_vals)

                # Update x_psm_0211_onboarding_state if pending
                if employee.x_psm_0211_onboarding_state == 'pending':
                    employee.sudo().write({'x_psm_0211_onboarding_state': 'submitted'})
                    
                employee.sudo().message_post(
                    body=f'📎 Documents updated via portal (Round {employee.x_psm_portal_revision_count}). '
                         f'({len(update_vals) // 2} fields updated)'
                )

            return request.redirect('/my/onboard_info/success?success=1')

        except Exception as e:
            _logger.exception("Portal upload error: %s", e)
            return request.redirect('/my/onboard_info?error=1#onboard')

    @http.route('/my/onboard_info/success', type='http', auth='user', website=True)
    def onboard_info_success_page(self, **kwargs):
        """Trang thông báo sau khi upload."""
        return request.render('M02_P0211.portal_onboard_info_success', {})

    @http.route(['/my/contract', '/my/contract/<int:employee_id>'], type='http', auth='user', website=True)
    def x_psm_portal_contract_page(self, employee_id=None, **kwargs):
        """Smart contract gateway:
        - Signed → redirect to /my/signatures (Odoo standard, clean list view)
        - Not signed → redirect to Odoo Sign UI
        - HR → can view any employee by /my/contract/<employee_id>
        """
        is_hr = request.env.user.has_group('hr.group_hr_user') or request.env.user.has_group('base.group_system')

        target_eid = employee_id or kwargs.get('employee_id')
        if is_hr and target_eid:
            employee = request.env['hr.employee'].sudo().browse(int(target_eid))
        else:
            employee = self._get_employee_for_portal_user()

        if not employee:
            return request.redirect('/my')

        # Ưu tiên trường x_psm_0211_contract_sign_request_id (custom flow)
        current_request = employee.x_psm_0211_contract_sign_request_id.sudo() if employee.x_psm_0211_contract_sign_request_id else None

        # Fallback: tìm qua sign.request.item theo partner của user (Odoo native flow)
        if not current_request:
            partner = request.env.user.partner_id
            sign_item = request.env['sign.request.item'].sudo().search([
                ('partner_id', '=', partner.id),
                ('sign_request_id.state', 'in', ['sent', 'signed']),
            ], order='create_date desc', limit=1)
            current_request = sign_item.sign_request_id if sign_item else None

        # Đã ký → dùng luôn /my/signatures của Odoo
        if current_request and current_request.state == 'signed':
            return request.redirect('/my/signatures')

        # Không có yêu cầu ký nào
        if not current_request:
            return request.redirect('/my?error=no_contract')

        # Chưa ký → redirect sang trang ký Odoo Sign
        partner = request.env.user.partner_id
        sign_item = current_request.request_item_ids.sudo().filtered(lambda r: r.partner_id == partner)

        # HR xem mà không phải người ký → redirect sang trang chi tiết
        if is_hr and not sign_item:
            return request.redirect(f'/my/signature/{current_request.id}')

        sign_item = sign_item[:1] or current_request.request_item_ids[:1]
        link_sign, _ = sign_item._get_sign_and_cancel_links(sign_item)
        
        # Chuyển trạng thái sang Signed nếu họ đã Passed (Done)
        if employee.x_psm_0211_onboarding_state == 'done':
            employee.sudo().write({'x_psm_0211_onboarding_state': 'signed'})
            
        connector = '&' if '?' in link_sign else '?'
        return request.redirect(f"{link_sign}{connector}portal=1")



