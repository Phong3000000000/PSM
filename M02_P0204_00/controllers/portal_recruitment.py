# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from odoo import http, exceptions, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class RecruitmentPortal(CustomerPortal):
    """Portal controller cho DM tạo Yêu Cầu Tuyển Dụng và Lịch PV"""

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

    def _portal_get_locked_department(self, user):
        """Return department locked by current user employee profile."""
        if not user or user._is_public():
            return request.env['hr.department'].sudo().browse(), _(
                "Không tìm thấy thông tin người dùng hợp lệ để xác định phòng ban."
            )

        employee = user.sudo().employee_id
        if not employee:
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        if not employee:
            return request.env['hr.department'].sudo().browse(), _(
                "Tài khoản của bạn chưa liên kết hồ sơ nhân viên. Vui lòng liên hệ HR để cấu hình."
            )

        if not employee.department_id:
            return request.env['hr.department'].sudo().browse(), _(
                "Tài khoản của bạn chưa được gán phòng ban trên hồ sơ nhân viên. Vui lòng liên hệ HR để cấu hình."
            )

        return employee.department_id.sudo(), False

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
    def portal_my_recruitment(self, page=1, search='', **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        _PER_PAGE = 10
        locked_department, locked_department_error = self._portal_get_locked_department(user)
        department_id = locked_department.id if locked_department else 0

        submit_status = kwargs.get('submit_status') or request.params.get('submit_status') or ''
        submit_message = kwargs.get('submit_message') or request.params.get('submit_message') or ''
        submit_request_id = self._to_int(kwargs.get('submit_request_id') or request.params.get('submit_request_id'), 0)
        submit_request_name = kwargs.get('submit_request_name') or request.params.get('submit_request_name') or ''

        active_tab = (kwargs.get('active_tab') or request.params.get('active_tab') or '').strip()
        expanded_request_id = self._to_int(kwargs.get('expanded_request_id') or request.params.get('expanded_request_id'), 0)
        if not expanded_request_id and submit_request_id:
            expanded_request_id = submit_request_id

        if active_tab not in ('jobs', 'history'):
            active_tab = 'history' if (submit_status in ('ok', 'success') or expanded_request_id) else 'jobs'

        job_model = request.env['hr.job'].sudo()
        request_model = request.env['x_psm_recruitment_request'].sudo() if 'x_psm_recruitment_request' in request.env else None

        request_state_labels = dict(request_model._fields['state'].selection) if request_model is not None else {}
        recruitment_block_labels = dict(request_model._fields['recruitment_block'].selection) if request_model is not None else {}

        approval_status_labels = {}
        if 'approval.request' in request.env:
            approval_model = request.env['approval.request']
            if 'request_status' in approval_model._fields:
                approval_status_labels = dict(approval_model._fields['request_status'].selection)

        approval_approver_status_labels = {}
        if 'approval.approver' in request.env:
            approval_approver_model = request.env['approval.approver']
            if 'status' in approval_approver_model._fields:
                approval_approver_status_labels = dict(approval_approver_model._fields['status'].selection)

        position_level_labels = {}
        if 'x_psm_recruitment_request_line' in request.env:
            request_line_model = request.env['x_psm_recruitment_request_line']
            if 'position_level' in request_line_model._fields:
                position_level_labels = dict(request_line_model._fields['position_level'].selection)

        job_position_level_labels = {}
        if 'position_level' in job_model._fields:
            job_position_level_labels = dict(job_model._fields['position_level'].selection)

        job_status_labels = {
            'hiring': _('Đang tuyển'),
            'not_hiring': _('Không tuyển'),
        }
        job_sort_labels = {
            'az': _('A-Z'),
            'za': _('Z-A'),
            'newest': _('Mới nhất'),
            'oldest': _('Cũ nhất'),
        }
        history_sort_labels = {
            'newest': _('Mới nhất'),
            'oldest': _('Cũ nhất'),
            'az': _('A-Z'),
            'za': _('Z-A'),
        }

        job_search = (kwargs.get('job_search') or request.params.get('job_search') or '').strip()
        job_position_level = (kwargs.get('job_position_level') or request.params.get('job_position_level') or '').strip()
        if job_position_level not in job_position_level_labels:
            job_position_level = ''
        job_status = (kwargs.get('job_status') or request.params.get('job_status') or '').strip()
        if job_status not in job_status_labels:
            job_status = ''
        job_sort = (kwargs.get('job_sort') or request.params.get('job_sort') or '').strip() or 'az'
        if job_sort not in job_sort_labels:
            job_sort = 'az'
        job_page = self._to_int(kwargs.get('job_page') or request.params.get('job_page'), self._to_int(page, 1))
        if job_page <= 0:
            job_page = 1

        history_search = (kwargs.get('history_search') or request.params.get('history_search') or '').strip()
        history_request_state = (kwargs.get('history_request_state') or request.params.get('history_request_state') or '').strip()
        if history_request_state and history_request_state not in request_state_labels:
            history_request_state = ''
        history_approval_state = (kwargs.get('history_approval_state') or request.params.get('history_approval_state') or '').strip()
        if history_approval_state and history_approval_state not in approval_status_labels:
            history_approval_state = ''
        history_sort = (kwargs.get('history_sort') or request.params.get('history_sort') or '').strip() or 'newest'
        if history_sort not in history_sort_labels:
            history_sort = 'newest'
        history_page = self._to_int(kwargs.get('history_page') or request.params.get('history_page'), 1)
        if history_page <= 0:
            history_page = 1

        # Job tab domain (khóa theo phòng ban gốc)
        jobs_domain = [('department_id', '!=', False), '|', ('recruitment_type', '=', 'store'), ('recruitment_type', '=', False)]

        allowed_depts = self._get_allowed_departments(user)

        # Khóa hiển thị theo đúng phòng ban gốc của employee.
        if department_id and department_id in allowed_depts.ids:
            jobs_domain += [('department_id', '=', department_id)]
        else:
            jobs_domain += [('id', '=', 0)]

        if job_search:
            jobs_domain += [('name', 'ilike', job_search)]
        if job_position_level:
            jobs_domain += [('position_level', '=', job_position_level)]
        if job_status == 'hiring':
            jobs_domain += [('no_of_recruitment', '>', 0)]
        elif job_status == 'not_hiring':
            jobs_domain += [('no_of_recruitment', '<=', 0)]

        job_order_map = {
            'az': 'name asc, id asc',
            'za': 'name desc, id desc',
            'newest': 'create_date desc, id desc',
            'oldest': 'create_date asc, id asc',
        }
        jobs_order = job_order_map.get(job_sort, 'name asc, id asc')

        jobs_query = {
            'active_tab': 'jobs',
            'job_search': job_search,
            'job_position_level': job_position_level,
            'job_status': job_status,
            'job_sort': job_sort,
            'job_page': job_page,
            'history_search': history_search,
            'history_request_state': history_request_state,
            'history_approval_state': history_approval_state,
            'history_sort': history_sort,
            'history_page': history_page,
            'expanded_request_id': expanded_request_id,
        }

        jobs_total = job_model.search_count(jobs_domain)
        jobs_pager = self._build_local_pager(
            total=jobs_total,
            page=job_page,
            step=_PER_PAGE,
            url='/my/recruitment',
            query_params=jobs_query,
            page_param='job_page',
        )

        jobs = job_model.search(
            jobs_domain,
            order=jobs_order,
            limit=_PER_PAGE,
            offset=jobs_pager['offset'],
        )

        departments = locked_department if locked_department else request.env['hr.department'].sudo().browse()
        companies = user.company_ids

        # Form portal luôn khóa theo phòng ban gốc của employee hiện tại.
        template_domain = [('id', '=', 0)]
        if locked_department:
            template_domain = [
                ('department_id', '=', locked_department.id),
                ('department_id', '!=', False),
                '|', ('recruitment_type', '=', 'store'), ('recruitment_type', '=', False)
            ]

        job_templates = request.env['hr.job'].sudo().search(
            template_domain,
            order='department_id, name asc'
        )

        work_locations = []
        try:
            work_locations = request.env['hr.work.location'].sudo().search([], order='name asc')
        except Exception:
            pass

        recruitment_requests = []
        approval_form_url_map = {}
        history_total = 0
        history_order_map = {
            'newest': 'create_date desc, id desc',
            'oldest': 'create_date asc, id asc',
            'az': 'name asc, id asc',
            'za': 'name desc, id desc',
        }
        history_order = history_order_map.get(history_sort, 'create_date desc, id desc')

        history_query = {
            'active_tab': 'history',
            'job_search': job_search,
            'job_position_level': job_position_level,
            'job_status': job_status,
            'job_sort': job_sort,
            'job_page': job_page,
            'history_search': history_search,
            'history_request_state': history_request_state,
            'history_approval_state': history_approval_state,
            'history_sort': history_sort,
            'history_page': history_page,
            'expanded_request_id': expanded_request_id,
        }

        if request_model is not None:
            history_domain = [
                ('user_id', '=', user.id),
                ('recruitment_block', '=', 'store'),
            ]
            if history_search:
                history_domain += ['|', '|',
                    ('name', 'ilike', history_search),
                    ('reason', 'ilike', history_search),
                    ('job_id.name', 'ilike', history_search),
                ]
            if history_request_state:
                history_domain += [('state', '=', history_request_state)]
            if history_approval_state:
                history_domain += [('x_psm_approval_status', '=', history_approval_state)]

            history_total = request_model.search_count(history_domain)
            history_pager = self._build_local_pager(
                total=history_total,
                page=history_page,
                step=_PER_PAGE,
                url='/my/recruitment',
                query_params=history_query,
                page_param='history_page',
            )

            recruitment_requests = request_model.search(
                history_domain,
                order=history_order,
                limit=_PER_PAGE,
                offset=history_pager['offset'],
            )
        else:
            history_pager = self._build_local_pager(
                total=0,
                page=history_page,
                step=_PER_PAGE,
                url='/my/recruitment',
                query_params=history_query,
                page_param='history_page',
            )

        if expanded_request_id:
            current_request_ids = recruitment_requests.ids if hasattr(recruitment_requests, 'ids') else []
            if expanded_request_id not in current_request_ids:
                expanded_request_id = False

        for req in recruitment_requests:
            if req.x_psm_approval_request_id:
                approval_form_url_map[req.id] = '/web#id=%s&model=approval.request&view_type=form' % req.x_psm_approval_request_id.id

        return request.render('M02_P0204_00.portal_my_recruitment', {
            'jobs': jobs,
            'jobs_pager': jobs_pager,
            'search': job_search,
            'department_id': department_id,
            'companies': companies,
            'departments': departments,
            'job_templates': job_templates,
            'work_locations': work_locations,
            'locked_department': locked_department,
            'locked_department_error': locked_department_error,
            'page_name': 'recruitment',
            'submit_status': submit_status,
            'submit_message': submit_message,
            'submit_request_id': submit_request_id,
            'submit_request_name': submit_request_name,
            'active_tab': active_tab,
            'expanded_request_id': expanded_request_id,
            'job_search': job_search,
            'job_position_level': job_position_level,
            'job_status': job_status,
            'job_sort': job_sort,
            'job_position_level_labels': job_position_level_labels,
            'job_status_labels': job_status_labels,
            'job_sort_labels': job_sort_labels,
            'jobs_total': jobs_total,
            'history_search': history_search,
            'history_request_state': history_request_state,
            'history_approval_state': history_approval_state,
            'history_sort': history_sort,
            'history_sort_labels': history_sort_labels,
            'history_total': history_total,
            'history_pager': history_pager,
            'recruitment_requests': recruitment_requests,
            'request_state_labels': request_state_labels,
            'approval_status_labels': approval_status_labels,
            'recruitment_block_labels': recruitment_block_labels,
            'position_level_labels': position_level_labels,
            'approval_approver_status_labels': approval_approver_status_labels,
            'approval_form_url_map': approval_form_url_map,
        })

    def _to_int(self, value, default=0):
        try:
            return int(value or default)
        except (TypeError, ValueError):
            return default

    def _build_local_pager(self, total, page, step, url, query_params, page_param):
        step = max(int(step or 10), 1)
        total = max(int(total or 0), 0)
        page_count = max(1, (total + step - 1) // step)
        page = max(1, min(int(page or 1), page_count))
        offset = (page - 1) * step

        def _url_for(target_page):
            params = dict(query_params or {})
            params[page_param] = target_page
            cleaned_params = {}
            for key, value in params.items():
                if value in (None, '', False):
                    continue
                cleaned_params[key] = value
            query = urlencode(cleaned_params)
            return '%s?%s' % (url, query) if query else url

        start = max(1, page - 2)
        end = min(page_count, page + 2)
        while (end - start) < 4 and start > 1:
            start -= 1
        while (end - start) < 4 and end < page_count:
            end += 1

        pages = [
            {
                'number': page_number,
                'url': _url_for(page_number),
                'is_current': page_number == page,
            }
            for page_number in range(start, end + 1)
        ]

        return {
            'page': page,
            'page_count': page_count,
            'total': total,
            'step': step,
            'offset': offset,
            'has_previous': page > 1,
            'has_next': page < page_count,
            'previous_url': _url_for(page - 1) if page > 1 else False,
            'next_url': _url_for(page + 1) if page < page_count else False,
            'pages': pages,
        }

    def _portal_get_valid_jobs_for_department(self, department_id):
        if not department_id:
            return request.env['hr.job'].sudo().browse()
        return request.env['hr.job'].sudo().search([
            ('department_id', '=', department_id),
            '|', ('recruitment_type', '=', 'store'), ('recruitment_type', '=', False),
        ])

    def _portal_collect_request_line_commands(self, post, department_id):
        form = request.httprequest.form
        line_job_ids = form.getlist('line_job_id[]')
        line_quantities = form.getlist('line_quantity[]')
        line_levels = form.getlist('line_position_level[]')
        line_locations = form.getlist('line_work_location_id[]')
        line_reasons = form.getlist('line_reason[]')

        if not any([line_job_ids, line_quantities, line_levels, line_locations, line_reasons]):
            # Backward compatibility for old single-line form payload.
            line_job_ids = [post.get('job_id') or '']
            line_quantities = [post.get('no_of_recruitment', '1')]
            line_levels = [post.get('position_level', '')]
            line_locations = [post.get('work_location_id', '')]
            line_reasons = [post.get('reason', '')]

        max_len = max(
            len(line_job_ids),
            len(line_quantities),
            len(line_levels),
            len(line_locations),
            len(line_reasons),
            1,
        )

        department_jobs = self._portal_get_valid_jobs_for_department(department_id)
        valid_job_ids = set(department_jobs.ids)
        if not valid_job_ids:
            return [], _("Phòng ban chưa có vị trí tuyển dụng được cấu hình. Vui lòng cấu hình vị trí trước khi tạo yêu cầu.")

        line_model = request.env['x_psm_recruitment_request_line']
        line_commands = []
        missing_job_selection = False
        invalid_job_selection = False
        for index in range(max_len):
            raw_job_id = (line_job_ids[index] if index < len(line_job_ids) else '').strip()
            job_id = self._to_int(raw_job_id, 0)

            quantity = max(self._to_int(line_quantities[index] if index < len(line_quantities) else 1, 1), 1)
            position_level = (line_levels[index] if index < len(line_levels) else '').strip()
            line_reason = (line_reasons[index] if index < len(line_reasons) else '').strip()
            work_location_id = self._to_int(line_locations[index] if index < len(line_locations) else 0, 0)

            if position_level not in ('management', 'staff'):
                position_level = False

            if not job_id:
                missing_job_selection = True
                continue

            if job_id not in valid_job_ids:
                invalid_job_selection = True
                _logger.warning(
                    'Portal request line skipped: invalid job %s for department %s',
                    job_id,
                    department_id,
                )
                continue

            job = department_jobs.browse(job_id)
            if not position_level and 'position_level' in job._fields:
                position_level = job.position_level or False
            if not work_location_id and 'work_location_id' in job._fields and job.work_location_id:
                work_location_id = job.work_location_id.id

            line_vals = {
                'department_id': department_id,
                'quantity': quantity,
                'recruitment_block': 'store',
                'job_id': job_id,
            }
            if position_level:
                line_vals['position_level'] = position_level
            if line_reason:
                line_vals['reason'] = line_reason
            if work_location_id and 'work_location_id' in line_model._fields:
                line_vals['work_location_id'] = work_location_id

            line_commands.append((0, 0, line_vals))

        if not line_commands:
            if missing_job_selection or invalid_job_selection:
                return [], _("Vui lòng chọn vị trí có sẵn đã được cấu hình cho từng dòng tuyển dụng.")
            return [], _("Phòng ban chưa có vị trí tuyển dụng được cấu hình. Vui lòng cấu hình vị trí trước khi tạo yêu cầu.")

        return line_commands, False

    def _portal_create_recruitment_request(self, user, post, department_id):
        if 'x_psm_recruitment_request' not in request.env:
            return False, _("Hệ thống chưa sẵn sàng tạo yêu cầu tuyển dụng.")

        line_commands, line_error = self._portal_collect_request_line_commands(post, department_id)
        if line_error:
            _logger.warning(
                'Portal request create skipped for dept %s: %s',
                department_id,
                line_error,
            )
            return False, line_error

        recruitment_block = post.get('recruitment_block') or post.get('recruitment_type') or 'store'
        if recruitment_block not in ('store', 'office'):
            recruitment_block = 'store'

        department = request.env['hr.department'].sudo().browse(department_id)
        company_id = department.company_id.id or request.env.company.id
        request_reason = (post.get('request_reason') or post.get('reason') or '').strip()
        if not request_reason:
            request_reason = 'Yêu cầu tuyển dụng tạo từ Portal.'

        request_vals = {
            'request_type': 'unplanned',
            'recruitment_block': recruitment_block,
            'department_id': department_id,
            'company_id': company_id,
            'user_id': user.id,
            'reason': request_reason,
            'line_ids': line_commands,
        }

        header_job_id = False
        for _command, _sequence, line_vals in line_commands:
            if line_vals.get('job_id'):
                header_job_id = line_vals.get('job_id')
                break
        if header_job_id:
            request_vals['job_id'] = header_job_id
            request_vals['quantity'] = sum(
                line_vals.get('quantity', 0)
                for _command, _sequence, line_vals in line_commands
                if line_vals.get('job_id') == header_job_id
            )

        recruitment_request = request.env['x_psm_recruitment_request'].sudo().create(request_vals)
        try:
            recruitment_request.sudo().action_submit()
        except exceptions.UserError as error:
            error_message = str(error)
            recruitment_request.sudo().message_post(
                body=_("Portal submit thất bại: %s") % error_message,
                message_type='comment',
            )
            _logger.warning(
                'Portal created request %s but cannot submit approval: %s',
                recruitment_request.id,
                error_message,
            )
            return recruitment_request, error_message
        except Exception as error:
            recruitment_request.sudo().message_post(
                body=_("Portal submit thất bại do lỗi hệ thống. Vui lòng kiểm tra log server."),
                message_type='comment',
            )
            _logger.exception('Portal request auto-submit error for %s', recruitment_request.id)
            return recruitment_request, _("Lỗi hệ thống khi gửi duyệt yêu cầu. Vui lòng liên hệ quản trị viên.")

        approval_request = recruitment_request.x_psm_approval_request_id
        approval_status = recruitment_request.x_psm_approval_status

        # Portal submit is successful when an approval request is created.
        # Store requests intentionally stay in draft while approval is pending.
        if not approval_request:
            error_message = _("Yêu cầu đã tạo nhưng chưa gửi duyệt thành công. Vui lòng kiểm tra lại.")
            recruitment_request.sudo().message_post(
                body=_("Portal submit chưa hoàn tất: chưa tạo được approval request."),
                message_type='comment',
            )
            _logger.error(
                'Portal submit incomplete for request %s: missing approval request (state=%s)',
                recruitment_request.id,
                recruitment_request.state,
            )
            return recruitment_request, error_message

        if recruitment_block == 'store':
            if approval_status in ('refused', 'cancel'):
                error_message = _("Yêu cầu đã tạo nhưng luồng duyệt đang ở trạng thái không hợp lệ. Vui lòng kiểm tra lại.")
                recruitment_request.sudo().message_post(
                    body=_("Portal submit chưa hoàn tất cho Store: approval ở trạng thái bất thường (%s).") % approval_status,
                    message_type='comment',
                )
                _logger.error(
                    'Portal submit invalid store approval status for request %s: status=%s state=%s approval_id=%s',
                    recruitment_request.id,
                    approval_status,
                    recruitment_request.state,
                    approval_request.id,
                )
                return recruitment_request, error_message
            return recruitment_request, False

        # Office flow keeps stricter checks but is no longer coupled to draft state alone.
        if approval_status not in ('pending', 'approved', 'new'):
            error_message = _("Yêu cầu đã tạo nhưng chưa gửi duyệt thành công. Vui lòng kiểm tra lại.")
            recruitment_request.sudo().message_post(
                body=_("Portal submit chưa hoàn tất cho Office: trạng thái approval hiện tại là %s.") % (approval_status or 'empty'),
                message_type='comment',
            )
            _logger.error(
                'Portal submit incomplete for office request %s: state=%s approval_status=%s approval_id=%s',
                recruitment_request.id,
                recruitment_request.state,
                approval_status,
                approval_request.id,
            )
            return recruitment_request, error_message

        return recruitment_request, False

    @http.route('/my/recruitment/create', type='http', auth='user', website=True, methods=['POST'])
    def portal_create_job(self, **post):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        locked_department, locked_department_error = self._portal_get_locked_department(user)
        if locked_department_error or not locked_department:
            return request.redirect('/my/recruitment?%s' % urlencode({
                'submit_status': 'error',
                'submit_message': locked_department_error or _(
                    'Không thể xác định phòng ban bị khóa cho tài khoản hiện tại.'
                ),
            }))

        department_id = locked_department.id

        allowed_depts = self._get_allowed_departments(user)
        if not department_id or department_id not in allowed_depts.ids:
            _logger.warning('Portal create job denied: user %s cannot access department %s', user.id, department_id)
            return request.redirect('/my/recruitment?%s' % urlencode({
                'submit_status': 'error',
                'submit_message': _(
                    'Bạn không có quyền tạo yêu cầu tuyển dụng cho phòng ban đang bị khóa.'
                ),
            }))

        if 'x_psm_recruitment_request' not in request.env:
            _logger.error('Portal recruitment request model x_psm_recruitment_request is unavailable')
            return request.redirect('/my/recruitment?%s' % urlencode({
                'submit_status': 'error',
                'submit_message': _("Thiếu mô hình yêu cầu tuyển dụng chuẩn (x_psm_recruitment_request). Vui lòng kiểm tra module M02_P0205_00."),
            }))

        req, submit_error = self._portal_create_recruitment_request(user, post, department_id)
        if req:
            _logger.info('Portal created recruitment request %s for dept %s', req.id, department_id)
        if submit_error:
            query = {'submit_status': 'error', 'submit_message': submit_error}
            if req:
                query['submit_request_id'] = req.id
                query['submit_request_name'] = req.name or ''
            return request.redirect('/my/recruitment?%s' % urlencode(query))
        if req:
            return request.redirect('/my/recruitment?%s' % urlencode({
                'submit_status': 'ok',
                'submit_request_id': req.id,
                'submit_request_name': req.name or '',
            }))
        return request.redirect('/my/recruitment?%s' % urlencode({
            'submit_status': 'error',
            'submit_message': _("Không thể tạo yêu cầu tuyển dụng từ dữ liệu đã nhập."),
        }))

    @http.route('/my/recruitment/<int:job_id>/delete', type='http', auth='user', website=True)
    def portal_delete_job(self, job_id, **kwargs):
        user = request.env.user
        if not user.x_is_portal_manager:
            return request.redirect('/my')

        allowed_depts = self._get_allowed_departments(user)
        job = request.env['hr.job'].sudo().browse(job_id)
        if job.exists() and job.department_id.id in allowed_depts.ids:
            # Archive instead of hard delete to avoid removing linked recruitment history.
            job.sudo().write({'active': False})
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

