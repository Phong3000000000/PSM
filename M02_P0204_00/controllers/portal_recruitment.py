# -*- coding: utf-8 -*-
from odoo import http, exceptions
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class RecruitmentPortal(CustomerPortal):
    """Portal controller cho DM tạo Job Position và Lịch PV"""

    def _get_allowed_departments(self, user):
        """Helper để lấy danh sách các department mà user có quyền truy cập (theo sơ đồ tổ chức)"""
        if not user or user._is_public():
            return request.env['hr.department'].sudo().browse()
            
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        
        dept_domain = []
        if employee:
            # Cho phép thấy phòng ban của chính mình, phòng ban mình trực tiếp quản lý,
            # và các phòng ban mà mình làm quản lý cấp 2 (RGM), cấp 3.
            dept_domain = ['|', '|', '|',
                ('id', '=', employee.department_id.id),
                ('manager_id', '=', employee.id),
                ('parent_id.manager_id', '=', employee.id),
                ('parent_id.parent_id.manager_id', '=', employee.id)
            ]
        else:
            dept_domain = ['|', '|',
                ('manager_id.user_id', '=', user.id),
                ('parent_id.manager_id.user_id', '=', user.id),
                ('parent_id.parent_id.manager_id.user_id', '=', user.id)
            ]
            
        return request.env['hr.department'].sudo().search(dept_domain)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        if user.x_is_portal_manager:
            allowed_depts = self._get_allowed_departments(user)
            dept_ids_domain = [('department_id', 'in', allowed_depts.ids)] if allowed_depts else [('id', '=', 0)]
            
            if 'job_count' in counters:
                domain = dept_ids_domain + [('department_id', '!=', False), '|', ('recruitment_type', '=', 'store'), ('recruitment_type', '=', False)]
                values['job_count'] = request.env['hr.job'].sudo().search_count(domain)
            if 'schedule_count' in counters:
                domain = dept_ids_domain
                values['schedule_count'] = request.env['interview.schedule'].sudo().search_count(domain)
        return values

    # ─────────────────────────────────────────────
    # JOB POSITIONS
    # ─────────────────────────────────────────────
    @http.route(['/my/recruitment', '/my/recruitment/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_recruitment(self, page=1, search='', department_id=0, **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        _PER_PAGE = 10
        page = int(page or 1)
        department_id = int(department_id or 0)

        # Không lọc theo create_uid nữa vì hiển thị hr.job
        domain = [('department_id', '!=', False), '|', ('recruitment_type', '=', 'store'), ('recruitment_type', '=', False)]
        
        allowed_depts = self._get_allowed_departments(user)

        # Removed ensure_department_templates call as per logic removal in hr_job.py

        if allowed_depts:
            domain += [('department_id', 'in', allowed_depts.ids)]
        else:
            domain += [('id', '=', 0)] # No access if no departments

        if search:
            domain += [('name', 'ilike', search)]
        if department_id:
            domain += [('department_id', '=', department_id)]

        # Sửa để hiển thị hr.job thay vì job.approval.request
        total = request.env['hr.job'].sudo().search_count(domain)
        pager = portal_pager(
            url='/my/recruitment',
            url_args={'search': search, 'department_id': department_id},
            total=total,
            page=page,
            step=_PER_PAGE,
        )
        jobs = request.env['hr.job'].sudo().search(
            domain, order='department_id, name asc',
            limit=_PER_PAGE, offset=pager['offset']
        )

        departments = allowed_depts
        companies = user.company_ids
        
        # Lọc job templates theo department user quản lý + khối cửa hàng
        template_domain = [('id', '=', 0)]
        if departments:
            template_domain = [
                ('department_id', 'in', departments.ids),
                ('department_id', '!=', False),
                '|', ('recruitment_type', '=', 'store'), ('recruitment_type', '=', False)
            ]
            if department_id:
                template_domain.append(('department_id', '=', department_id))

            job_templates = request.env['hr.job'].sudo().search(
                template_domain,
                order='department_id, name asc'
            )
        else:
            job_templates = request.env['hr.job'].sudo().browse()

        work_locations = []
        try:
            work_locations = request.env['hr.work.location'].sudo().search([], order='name asc')
        except Exception:
            pass

        # Thêm: Lấy luôn danh sách Master Job (hr.job global) để dự phòng khi Dept chưa có Job con
        master_templates = request.env['hr.job'].sudo().search([('department_id', '=', False)], order='name asc')

        return request.render('M02_P0204_00.portal_my_recruitment', {
            'jobs': jobs,
            'pager': pager,
            'search': search,
            'department_id': department_id,
            'companies': companies,
            'departments': departments,
            'job_templates': job_templates,
            'master_templates': master_templates,
            'work_locations': work_locations,
            'page_name': 'recruitment',
        })


    @http.route('/my/recruitment/create', type='http', auth='user', website=True, methods=['POST'])
    def portal_create_job(self, **post):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        name = post.get('name', '').strip()
        department_id = int(post.get('department_id', 0) or 0)
        no_of_recruitment = int(post.get('no_of_recruitment', 1) or 1)
        recruitment_type = post.get('recruitment_type', 'store') or 'store'
        position_level = post.get('position_level') or False
        
        # Gán Mặc định bộ phận của User đang đăng nhập nếu DM tạo (Nếu DM không tự chọn)
        if not department_id:
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
            if employee and employee.department_id:
                department_id = employee.department_id.id

        allowed_depts = self._get_allowed_departments(user)
        if not department_id or department_id not in allowed_depts.ids:
            _logger.warning('Portal create job denied: user %s cannot access department %s', user.id, department_id)
            return request.redirect('/my/recruitment')

        if name and department_id:
            department = request.env['hr.department'].sudo().browse(department_id)
            company_id = department.company_id.id or request.env.company.id
            # Portal chỉ tạo yêu cầu tuyển dụng, KHÔNG cập nhật hr.job ngay.
            vals = {
                'name': name,
                'company_id': company_id,
                'department_id': department_id,
                'no_of_recruitment': no_of_recruitment,
                'recruitment_type': recruitment_type,
                'state': 'submitted',
                'requester_user_id': user.id,
            }
            if position_level:
                vals['position_level'] = position_level

            try:
                req = request.env['job.approval.request'].sudo().create(vals)
                _logger.info(
                    'Portal created job approval request %s (%s) for dept %s',
                    req.id, name, department.name,
                )
            except Exception as e:
                _logger.error('Portal create approval request error: %s', e)

        return request.redirect('/my/recruitment')

    @http.route('/my/recruitment/<int:job_id>/delete', type='http', auth='user', website=True)
    def portal_delete_job(self, job_id, **kwargs):
        user = request.env.user
        job = request.env['job.approval.request'].sudo().browse(job_id)
        if job.exists():
            job.sudo().unlink()
        return request.redirect('/my/recruitment')

    # ─────────────────────────────────────────────
    # INTERVIEW SCHEDULES
    # ─────────────────────────────────────────────
    @http.route(['/my/interview-schedule', '/my/interview-schedule/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_interview_schedule(self, page=1, search='', department_id=0, state='', **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        _PER_PAGE = 10
        page = int(page or 1)
        department_id = int(department_id or 0)

        domain = []
        allowed_depts = self._get_allowed_departments(user)
        if allowed_depts:
            domain += [('department_id', 'in', allowed_depts.ids)]
        else:
            domain += [('id', '=', 0)]
        if search:
            domain += [('name', 'ilike', search)]
        if department_id:
            domain += [('department_id', '=', department_id)]
        if state:
            domain += [('state', '=', state)]

        total = request.env['interview.schedule'].sudo().search_count(domain)
        pager = portal_pager(
            url='/my/interview-schedule',
            url_args={'search': search, 'department_id': department_id, 'state': state},
            total=total,
            page=page,
            step=_PER_PAGE,
        )
        schedules = request.env['interview.schedule'].sudo().search(
            domain, order='week_start_date desc',
            limit=_PER_PAGE, offset=pager['offset']
        )
        companies = user.company_ids

        departments = allowed_depts

        return request.render('M02_P0204_00.portal_my_interview_schedule', {
            'schedules': schedules,
            'pager': pager,
            'search': search,
            'department_id': department_id,
            'state': state,
            'companies': companies,
            'departments': departments,
            'page_name': 'interview_schedule',
        })


    @http.route('/my/interview-schedule/create', type='http', auth='user', website=True, methods=['POST'])
    def portal_create_interview_schedule(self, **post):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        schedule_id = int(post.get('schedule_id', 0) or 0)
        department_id = int(post.get('department_id', 0) or 0)
        # week_start_date: ngày Thứ Hai của tuần (YYYY-MM-DD)
        week_start_date = post.get('week_start_date', '') or False

        def parse_dt(val):
            """dd/m/yyyy hh:mm AM/PM → UTC string cho Odoo (UTC+7)"""
            if not val:
                return False
            try:
                # Localize to Vietnam time then convert to UTC
                import pytz
                tz = pytz.timezone('Asia/Ho_Chi_Minh')
                dt = datetime.strptime(val, '%d/%m/%Y %I:%M %p')
                dt = tz.localize(dt).astimezone(pytz.utc)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return False

        interview_date_1 = parse_dt(post.get('interview_date_1'))
        interview_date_2 = parse_dt(post.get('interview_date_2'))
        interview_date_3 = parse_dt(post.get('interview_date_3'))
        max_candidates_slot_1 = int(post.get('max_candidates_slot_1', 1) or 1)
        max_candidates_slot_2 = int(post.get('max_candidates_slot_2', 1) or 1)
        max_candidates_slot_3 = int(post.get('max_candidates_slot_3', 1) or 1)

        if not department_id:
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
            if employee and employee.department_id:
                department_id = employee.department_id.id

        allowed_depts = self._get_allowed_departments(user)
        if not department_id or department_id not in allowed_depts.ids:
            _logger.warning('Portal update schedule denied: user %s cannot access department %s', user.id, department_id)
            return request.redirect('/my/interview-schedule')

        if department_id and week_start_date:
            try:
                vals = {}
                if interview_date_1:
                    vals['interview_date_1'] = interview_date_1
                if interview_date_2:
                    vals['interview_date_2'] = interview_date_2
                if interview_date_3:
                    vals['interview_date_3'] = interview_date_3
                vals['max_candidates_slot_1'] = max(0, max_candidates_slot_1)
                vals['max_candidates_slot_2'] = max(0, max_candidates_slot_2)
                vals['max_candidates_slot_3'] = max(0, max_candidates_slot_3)

                schedule = request.env['interview.schedule'].sudo().browse(schedule_id) if schedule_id else request.env['interview.schedule'].sudo().browse()
                if schedule and schedule.exists():
                    # Bảo vệ: chỉ cho cập nhật lịch thuộc phòng ban user được phép.
                    if schedule.department_id.id not in allowed_depts.ids:
                        _logger.warning('Portal update schedule denied: user %s cannot access schedule %s', user.id, schedule.id)
                        return request.redirect('/my/interview-schedule')
                else:
                    schedule_domain = [
                        ('department_id', '=', department_id),
                        ('week_start_date', '=', week_start_date),
                    ]
                    schedule = request.env['interview.schedule'].sudo().search(
                        schedule_domain,
                        order='id desc',
                        limit=1,
                    )

                # Chỉ cập nhật lịch đã được tạo sẵn từ internal.
                if schedule:
                    vals['state'] = 'draft'
                    schedule.write(vals)
                    _logger.info(
                        'Portal updated interview schedule %s for dept=%s week=%s',
                        schedule.id,
                        department_id,
                        week_start_date,
                    )
                else:
                    _logger.warning(
                        'No pre-created interview schedule found for dept=%s week=%s',
                        department_id,
                        week_start_date,
                    )
            except Exception as e:
                _logger.error('Portal update schedule error: %s', e)

        return request.redirect('/my/interview-schedule')

    @http.route('/my/interview-schedule/<int:schedule_id>/confirm', type='http', auth='user', website=True)
    def portal_confirm_schedule(self, schedule_id, **kwargs):
        user = request.env.user
        schedule = request.env['interview.schedule'].sudo().browse(schedule_id)
        if schedule.exists():
            try:
                schedule.sudo().write({'state': 'confirmed'})
            except Exception as e:
                _logger.error('Portal confirm schedule error: %s', e)
        return request.redirect('/my/interview-schedule')

    @http.route('/recruitment/interview/accept/<string:token>', type='http', auth='public', website=True, csrf=False)
    def portal_accept_interview(self, token, **kwargs):
        applicant = request.env['hr.applicant'].sudo().search([
            ('interview_accept_token', '=', token)
        ], limit=1)

        values = {
            'status': 'error',
            'message': 'Liên kết xác nhận không hợp lệ hoặc đã hết hiệu lực.',
            'applicant': applicant,
            'event': request.env['calendar.event'].sudo().browse(),
        }

        if not applicant:
            return request.render('M02_P0204_00.portal_interview_accept_result', values)

        try:
            event = applicant.sudo().action_accept_interview_confirmation()
            values.update({
                'status': 'success',
                'message': 'Xác nhận thành công. Lịch phỏng vấn đã được tạo trên hệ thống.',
                'event': event,
            })
        except exceptions.UserError as e:
            values['message'] = str(e)
        except Exception as e:
            _logger.error('Interview accept failed for applicant %s: %s', applicant.id, e)
            values['message'] = 'Hệ thống chưa thể xử lý yêu cầu xác nhận lúc này. Vui lòng liên hệ HR.'

        return request.render('M02_P0204_00.portal_interview_accept_result', values)

    # ─────────────────────────────────────────────
    # OJE EVALUATION
    # ─────────────────────────────────────────────
    def _get_dm_oje_applicants(self, user):
        """Trả về applicants mà user này được chỉ định làm evaluator OJE."""
        # Ưu tiên kiểm tra oje_evaluator_user_id (Snapshot từ Job)
        # fallback: department manager (cho các bản ghi cũ hoặc nếu chưa gán evaluator)
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1
        )
        
        # Tìm stage có tên "OJE"
        oje_stages = request.env['hr.recruitment.stage'].sudo().search(
            [('name', 'ilike', 'OJE')]
        )
        
        domain = [('oje_evaluator_user_id', '=', user.id)]
        if employee:
            departments = self._get_allowed_departments(user)
            if departments:
                domain = ['|', ('department_id', 'in', departments.ids)] + domain
        
        # Thêm điều kiện: Phải ở stage OJE HOẶC đã có đánh giá
        if oje_stages:
            domain = ['&'] + domain + ['|', ('stage_id', 'in', oje_stages.ids), ('oje_evaluation_id', '!=', False)]
        else:
            domain = ['&'] + domain + [('oje_evaluation_id', '!=', False)]

        return request.env['hr.applicant'].sudo().search(domain, order='partner_name asc')

    def _should_use_internal_oje_form(self, applicant, evaluation=False):
        """Store OJE always uses the new internal form route."""
        job_scope = False
        if applicant and applicant.job_id and hasattr(applicant.job_id, '_get_oje_template_scope'):
            job_scope = applicant.job_id.sudo()._get_oje_template_scope()

        eval_scope = evaluation.template_scope if evaluation else False
        store_scopes = ('store_staff', 'store_management')
        return job_scope in store_scopes or eval_scope in store_scopes

    @http.route(['/my/oje-evaluation', '/my/oje-evaluation/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_oje_evaluation(self, page=1, search='', department_id=0, result='', **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        _PER_PAGE = 10 # Keep _PER_PAGE as it's used later
        page = int(page or 1)
        department_id = int(department_id or 0)

        # Cập nhật domain để tìm theo evaluator
        applicants_all = self._get_dm_oje_applicants(user)
        domain = [('id', 'in', applicants_all.ids)]

        if search:
            domain += [('partner_name', 'ilike', search)]
        
        if result == 'pass':
            domain += [('oje_result', '=', 'pass'), ('oje_evaluation_state', '=', 'done')]
        elif result == 'fail':
            domain += [('oje_result', '=', 'fail'), ('oje_evaluation_state', '=', 'done')]
        elif result == 'pending':
            domain += [('oje_evaluation_id', '=', False)]

        total = request.env['hr.applicant'].sudo().search_count(domain)
        pager = portal_pager(
            url='/my/oje-evaluation',
            url_args={'search': search, 'department_id': department_id, 'result': result},
            total=total,
            page=page,
            step=_PER_PAGE,
        )
        applicants = request.env['hr.applicant'].sudo().search(
            domain, order='partner_name asc',
            limit=_PER_PAGE, offset=pager['offset']
        )

        return request.render('M02_P0204_00.portal_my_oje_evaluation', {
            'applicants': applicants,
            'pager': pager,
            'search': search,
            'department_id': department_id,
            'result': result,
            'page_name': 'oje_evaluation',
        })

    @http.route('/my/oje-evaluation/start/<int:applicant_id>', type='http', auth='user', website=True)
    def portal_oje_start(self, applicant_id, **kwargs):
        """Khởi tạo phiếu đánh giá OJE từ cấu hình của Job"""
        user = request.env.user
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)
        if not applicant.exists() or not applicant.job_id:
            return request.redirect('/my/oje-evaluation')

        # Kiểm tra quyền: phải là evaluator hoặc DM
        allowed_applicants = self._get_dm_oje_applicants(user)
        if applicant not in allowed_applicants:
            return request.redirect('/my/oje-evaluation')

        evaluation = applicant.sudo()._ensure_oje_evaluation(evaluator_user=user)

        if self._should_use_internal_oje_form(applicant, evaluation):
            return request.redirect(f'/recruitment/oje/internal/{evaluation.id}')

        return request.redirect(f'/my/recruitment/oje/{applicant.id}')

    @http.route('/my/recruitment/oje/<int:applicant_id>', type='http', auth='user', website=True)
    def portal_oje_form(self, applicant_id, **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)
        if not applicant.exists():
            return request.redirect('/my/oje-evaluation')

        dm_applicants = self._get_dm_oje_applicants(user)
        if applicant not in dm_applicants:
            return request.redirect('/my/oje-evaluation')

        evaluation = applicant.sudo()._ensure_oje_evaluation(evaluator_user=user)
        if self._should_use_internal_oje_form(applicant, evaluation):
            return request.redirect(f'/recruitment/oje/internal/{evaluation.id}')

        evaluation = applicant.oje_evaluation_id
        if evaluation.state == 'done':
            return request.render('M02_P0204_00.portal_oje_form_readonly', {
                'applicant': applicant,
                'evaluation': evaluation,
                'page_name': 'oje_evaluation',
            })

        return request.render('M02_P0204_00.portal_oje_form', {
            'applicant': applicant,
            'evaluation': evaluation,
            'page_name': 'oje_evaluation',
        })

    @http.route('/my/recruitment/oje/submit', type='http', auth='user', methods=['POST'], website=True)
    def portal_oje_submit(self, **post):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        applicant_id = int(post.get('applicant_id', 0))
        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)
        if not applicant.exists() or not applicant.oje_evaluation_id:
            return request.redirect('/my/oje-evaluation')

        dm_applicants = self._get_dm_oje_applicants(user)
        if applicant not in dm_applicants:
            return request.redirect('/my/oje-evaluation')

        evaluation = applicant.oje_evaluation_id
        if self._should_use_internal_oje_form(applicant, evaluation):
            return request.redirect(f'/recruitment/oje/internal/{evaluation.id}')

        if evaluation.state == 'done':
            return request.redirect(f'/my/recruitment/oje/{applicant.id}')

        # Save answers
        for line in evaluation.line_ids:
            prefix = f"line_{line.id}_"
            if line.field_type == 'text':
                score_str = post.get(f"{prefix}score") or '0'
                try:
                    score_val = float(score_str)
                except ValueError:
                    score_val = 0.0
                line.write({
                    'text_value': post.get(f"{prefix}comment"),
                    'text_score': score_val,
                })
            elif line.field_type == 'checkbox':
                line.write({
                    'checkbox_value': True if post.get(f"{prefix}check") == 'on' else False,
                })
            elif line.field_type == 'radio':
                option_id = int(post.get(f"{prefix}option", 0))
                if option_id:
                    line.write({'selected_option_id': option_id})

        # Submit evaluation
        evaluation.action_submit()
        
        # Sau khi submit, redirect về trang danh sách hoặc trang kết quả
        return request.redirect(f'/my/oje-evaluation/{applicant.id}')

    @http.route('/my/oje-evaluation/<int:applicant_id>', type='http', auth='user', website=True)
    def portal_oje_applicant_detail(self, applicant_id, **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        applicant = request.env['hr.applicant'].sudo().browse(applicant_id)
        if not applicant.exists():
            return request.redirect('/my/oje-evaluation')

        # Kiểm tra quyền: applicant phải thuộc phòng ban DM
        dm_applicants = self._get_dm_oje_applicants(user)
        if applicant not in dm_applicants:
            return request.redirect('/my/oje-evaluation')

        return request.render('M02_P0204_00.portal_oje_applicant_detail', {
            'applicant': applicant,
            'page_name': 'oje_evaluation',
        })

