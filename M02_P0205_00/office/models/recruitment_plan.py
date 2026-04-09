# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions


class RecruitmentPlan(models.Model):
    _name = 'recruitment.plan'
    _description = 'Kế Hoạch Tuyển Dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Mã kế hoạch', required=True, copy=False, readonly=True,
        default=lambda self: 'New')

    # === One2many Lines ===
    line_ids = fields.One2many(
        'recruitment.plan.line', 'plan_id', string='Chi tiết kế hoạch')

    # === Additional useful fields ===
    priority = fields.Selection([
        ('0', 'Bình thường'),
        ('1', 'Khẩn cấp'),
        ('2', 'Rất khẩn cấp'),
    ], string='Độ ưu tiên', default='0', tracking=True)

    reason = fields.Text(
        string='Lý do / Ghi chú',
        help='Lý do tuyển dụng hoặc ghi chú bổ sung')

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('waiting_manager', 'Chờ Line Manager duyệt'),
        ('manager_approved', 'Manager đã duyệt'),
        ('hr_validation', 'HR Validate'),
        ('waiting_ceo', 'Chờ CEO duyệt'),
        ('in_progress', 'Đang tuyển'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company)
    user_id = fields.Many2one(
        'res.users', string='Người lập',
        default=lambda self: self.env.user, tracking=True)

    request_count = fields.Integer(string='Số lượng yêu cầu', default=0)
    job_count = fields.Integer(compute='_compute_job_count', string='Số lượng vị trí')
    total_quantity = fields.Integer(compute='_compute_total_quantity', string='Tổng số lượng', store=True)

    batch_id = fields.Many2one(
        'recruitment.batch', string='Đợt tuyển dụng',
        tracking=True,
        help='Chọn đợt tuyển dụng để tự động tải các vị trí từ Yêu Cầu Tuyển Dụng')
    
    date_submitted = fields.Datetime(string='Ngày gửi duyệt', readonly=True)
    is_reminder_sent = fields.Boolean(string='Đã gửi nhắc nhở', default=False)

    can_approve_as_manager = fields.Boolean(
        string='Có thể duyệt',
        compute='_compute_can_approve_as_manager',
        store=False,
    )

    # === Sub-plan fields ===

    parent_id = fields.Many2one(
        'recruitment.plan', string='Kế hoạch cha', ondelete='cascade', tracking=True)
    sub_plan_ids = fields.One2many(
        'recruitment.plan', 'parent_id', string='Kế hoạch con')
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban (Kế hoạch con)')
    is_sub_plan = fields.Boolean(
        string='Là kế hoạch con', default=False)

    @api.depends('state', 'is_sub_plan', 'department_id')
    def _compute_can_approve_as_manager(self):
        """Chỉ cho phép manager của phòng ban đó duyệt sub-plan tương ứng"""
        current_user = self.env.user
        for rec in self:
            if rec.state != 'waiting_manager':
                rec.can_approve_as_manager = False
                continue
            if rec.is_sub_plan and rec.department_id:
                # Sub-plan: chỉ manager của department đó mới được duyệt
                dept_manager = rec.department_id.manager_id
                rec.can_approve_as_manager = bool(
                    dept_manager and dept_manager.user_id == current_user
                )
            else:
                # Parent plan: không duyệt trực tiếp
                rec.can_approve_as_manager = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Skip sequence for sub-plans to allow custom naming or handled below
                if not vals.get('is_sub_plan'):
                    code = 'recruitment.plan'
                    name = self.env['ir.sequence'].next_by_code(code)
                    if not name:
                        # Auto-heal: Create sequence if missing
                        seq = self.env['ir.sequence'].sudo().search([('code', '=', code)], limit=1)
                        if not seq:
                            seq = self.env['ir.sequence'].sudo().create({
                                'name': 'Recruitment Plan',
                                'code': code,
                                'prefix': 'PLAN/%(year)s/',
                                'padding': 4,
                                'company_id': False,
                            })
                        name = seq.next_by_id()
                    vals['name'] = name or 'New'
        return super(RecruitmentPlan, self).create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and not self.env.context.get('skip_parent_sync'):
            for rec in self.filtered(lambda r: r.is_sub_plan and r.parent_id):
                rec._sync_parent_state()
        return res

    def _sync_parent_state(self):
        """Đồng bộ trạng thái parent = trạng thái thấp nhất (chậm nhất) trong các sub-plans."""
        parent = self.parent_id
        if not parent:
            return
        state_order = [
            'cancel', 'draft', 'waiting_manager', 'manager_approved',
            'hr_validation', 'waiting_ceo', 'in_progress', 'done'
        ]
        sibling_states = parent.sub_plan_ids.mapped('state')
        if not sibling_states:
            return

        def state_rank(s):
            try:
                return state_order.index(s)
            except ValueError:
                return 0

        min_state = min(sibling_states, key=state_rank)
        if parent.state != min_state:
            parent.with_context(skip_parent_sync=True).write({'state': min_state})

    @api.depends('line_ids.quantity')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))

    def _compute_job_count(self):
        for rec in self:
            rec.job_count = len(rec.line_ids.mapped('job_id'))

    def action_load_from_batch(self):
        """Tự động điền line_ids từ các YCTD có chọn đợt tuyển dụng này"""
        self.ensure_one()
        if not self.batch_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': 'Vui lòng chọn Đợt tuyển dụng trước.',
                    'sticky': False,
                    'type': 'warning',
                }
            }

        requests = self.env['recruitment.request'].search([
            ('batch_id', '=', self.batch_id.id),
            ('state', 'not in', ['cancel']),
        ])

        if not requests:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': 'Không có Yêu Cầu Tuyển Dụng nào thuộc đợt tuyển dụng này.',
                    'sticky': False,
                    'type': 'warning',
                }
            }

        # Xóa các dòng cũ rồi thêm mới
        self.line_ids.unlink()
        new_lines_vals = []
        for req in requests:
            if req.request_type == 'unplanned':
                new_lines_vals.append({
                    'plan_id': self.id,
                    'department_id': req.department_id.id,
                    'job_id': req.job_id.id,
                    'quantity': req.quantity,
                    'planned_date': fields.Date.today(),
                    'reason': req.reason or '',
                })
            else:
                # Đối với loại Theo kế hoạch, lấy từng dòng chi tiết
                for req_line in req.line_ids:
                    new_lines_vals.append({
                        'plan_id': self.id,
                        'department_id': req_line.department_id.id,
                        'job_id': req_line.job_id.id,
                        'quantity': req_line.quantity,
                        'planned_date': req_line.planned_date or fields.Date.today(),
                        'reason': req_line.reason or '',
                    })
        
        if new_lines_vals:
            self.env['recruitment.plan.line'].create(new_lines_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tải {len(new_lines_vals)} vị trí từ đợt tuyển dụng {self.batch_id.batch_name}.',
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
            }
        }

    def action_open_jobs(self):
        self.ensure_one()
        job_ids = self.line_ids.mapped('job_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vị trí tuyển dụng',
            'res_model': 'hr.job',
            'view_mode': 'list,form',
            'domain': [('id', 'in', job_ids)],
            'context': {'default_company_id': self.company_id.id},
        }

    def action_view_sub_plans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Kế hoạch con',
            'res_model': 'recruitment.plan',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_is_sub_plan': True,
                'default_priority': self.priority,
            },
        }

    # === Actions ===
    def action_notify_department_heads(self):
        """Public method to manually trigger notifications and create sub-plans if parent"""
        self.ensure_one()
        
        if not self.line_ids:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Cảnh báo',
                    'message': 'Vui lòng thêm ít nhất một vị trí tuyển dụng.',
                    'sticky': False,
                    'type': 'warning',
                }
            }

        # Rule: Planned Month must be at least 1 month after Submission Month
        today = fields.Date.today()
        for line in self.line_ids:
            if line.planned_date:
                planned_month_count = line.planned_date.year * 12 + line.planned_date.month
                current_month_count = today.year * 12 + today.month
                if planned_month_count <= current_month_count:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Cảnh báo',
                            'message': f'Vị trí {line.job_id.name} có thời gian dự kiến {line.planned_date} không hợp lệ. Phải gửi trước ít nhất 1 tháng.',
                            'sticky': False,
                            'type': 'danger',
                        }
                    }

        if self.is_sub_plan:
            # Sub-plan behavior: just notify managers and move to approval
            has_managers = self._notify_department_heads()
            self.write({
                'state': 'waiting_manager',
                'date_submitted': fields.Datetime.now()
            })
            self.line_ids.write({'state': 'waiting_manager'})
            message = 'Đã gửi thông báo cho Trưởng bộ phận duyệt.'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': message,
                    'sticky': False,
                    'type': 'success',
                    'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
                }
            }

        # Parent Plan behavior: Create sub-plans per department
        dept_lines = {}
        for line in self.line_ids:
            if line.department_id not in dept_lines:
                dept_lines[line.department_id] = []
            dept_lines[line.department_id].append(line)
        
        created_sub_count = 0
        for dept, lines in dept_lines.items():
            # Create sub-plan
            sub_plan_vals = {
                'name': f"{self.name} - {dept.name}",
                'parent_id': self.id,
                'is_sub_plan': True,
                'department_id': dept.id,
                'priority': self.priority,
                'reason': self.reason,
                'state': 'waiting_manager',
                'date_submitted': fields.Datetime.now(),
                'user_id': self.user_id.id,
                'company_id': self.company_id.id,
            }
            sub_plan = self.create([sub_plan_vals])
            
            # Create lines for sub-plan
            for line in lines:
                self.env['recruitment.plan.line'].create({
                    'plan_id': sub_plan.id,
                    'department_id': line.department_id.id,
                    'job_id': line.job_id.id,
                    'quantity': line.quantity,
                    'planned_date': line.planned_date,
                    'reason': line.reason,
                    'state': 'waiting_manager',
                })
            
            # Notify manager for this sub-plan
            sub_plan._notify_department_heads()
            created_sub_count += 1

        self.write({'state': 'waiting_manager'})
        self.line_ids.write({'state': 'waiting_manager'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tạo {created_sub_count} kế hoạch con và gửi thông báo cho các bộ phận.',
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
            }
        }

    def _notify_department_heads(self):
        """Send notifications and create activities for relevant department managers"""
        any_notified = False
        for rec in self:
            # 1. Get standard managers from the department manager_id field
            managers = rec.line_ids.mapped('department_id.manager_id.user_id')
            
            # 2. ALSO get users who have "Trưởng phòng" (Department Head) Job Position in those departments
            # as requested: "những người có Job Position là trưởng phòng"
            involved_depts = rec.line_ids.mapped('department_id')
            tp_employees = self.env['hr.employee'].sudo().search([
                ('department_id', 'in', involved_depts.ids),
                ('job_id.name', 'ilike', 'Trưởng phòng'),
                ('user_id', '!=', False)
            ])
            tp_users = tp_employees.mapped('user_id')
            
            # Combine all users to notify
            all_users = (managers | tp_users)
            
            if not all_users:
                continue
            
            any_notified = True
            # 1. Post a message in the chatter and mention the managers
            manager_mentions = ", ".join([f"@{m.display_name}" for m in all_users])
            msg = f"Kế hoạch tuyển dụng {rec.name} đã được gửi và đang chờ bạn phê duyệt: {manager_mentions}"
            rec.message_post(body=msg, partner_ids=all_users.partner_id.ids)

            # 2. Schedule an activity for each manager
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            for user in all_users:
                # Check if activity already exists to avoid duplicates if re-sent
                existing_activity = self.env['mail.activity'].sudo().search([
                    ('res_model_id', '=', self.env['ir.model']._get_id('recruitment.plan')),
                    ('res_id', '=', rec.id),
                    ('user_id', '=', user.id),
                    ('summary', '=', 'Duyệt kế hoạch tuyển dụng')
                ], limit=1)
                
                if not existing_activity:
                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env['ir.model']._get_id('recruitment.plan'),
                        'res_id': rec.id,
                        'user_id': user.id,
                        'summary': 'Duyệt kế hoạch tuyển dụng',
                        'note': f'Vui lòng xem xét và duyệt kế hoạch tuyển dụng {rec.name}.',
                        'activity_type_id': activity_type.id if activity_type else False,
                        'date_deadline': fields.Date.today(),
                    })
        return any_notified

    def action_manager_approve(self):
        self.ensure_one()
        current_user = self.env.user

        # Validate: chỉ manager của phòng ban mới được duyệt sub-plan
        if self.is_sub_plan and self.department_id:
            dept_manager = self.department_id.manager_id
            if not dept_manager or dept_manager.user_id != current_user:
                raise exceptions.UserError(
                    _("Bạn không phải Trưởng phòng của phòng ban '%s'. Chỉ %s mới có thể duyệt kế hoạch này.")
                    % (self.department_id.name, dept_manager.name if dept_manager else 'N/A')
                )

        # Xóa các dòng không được duyệt (is_approved = False)
        rejected_lines = self.line_ids.filtered(lambda l: not l.is_approved)
        rejected_lines.unlink()
        self.write({'state': 'manager_approved'})
        self.line_ids.write({'state': 'manager_approved'})

        # Cập nhật các dòng tương ứng trong parent plan (cùng phòng ban)
        if self.is_sub_plan and self.parent_id and self.department_id:
            parent_dept_lines = self.parent_id.line_ids.filtered(
                lambda l: l.department_id == self.department_id
            )
            parent_dept_lines.write({'state': 'manager_approved'})

        self.message_post(
            body=_("✓ %s đã duyệt kế hoạch tuyển dụng cho phòng ban %s.")
                 % (current_user.name, self.department_id.name if self.department_id else ''),
            message_type='notification'
        )

        # Nếu là sub-plan: kiểm tra tất cả sub-plans đã duyệt chưa
        if self.is_sub_plan and self.parent_id:
            sibling_subs = self.parent_id.sub_plan_ids
            all_subs_approved = all(s.state == 'manager_approved' for s in sibling_subs)
            if all_subs_approved:
                self.parent_id.with_context(skip_parent_sync=True).write({'state': 'manager_approved'})
                self.parent_id.message_post(
                    body=_("✓ Tất cả Trưởng phòng đã duyệt. Kế hoạch tuyển dụng chuyển sang HR Validate."),
                    message_type='notification'
                )
                # Gửi Activity cho HR
                self.parent_id._send_activity_to_hr_for_validation()
        elif not self.is_sub_plan:
            # Parent plan không có sub-plans: gửi thẳng activity cho HR
            self._send_activity_to_hr_for_validation()

    def _send_activity_to_hr_for_validation(self):
        """Gửi Activity cho tất cả HR users khi tất cả sub-plans được duyệt"""
        self.ensure_one()

        # Lấy cả HR Manager và HR Officer
        all_users = self.env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)])
        hr_users = all_users.filtered(
            lambda u: u.has_group('hr.group_hr_manager') or u.has_group('hr.group_hr_user')
        )
        if not hr_users:
            return

        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        res_model_id = self.env['ir.model']._get_id('recruitment.plan')

        for user in hr_users:
            # Tránh tạo duplicate activity
            existing = self.env['mail.activity'].sudo().search([
                ('res_model_id', '=', res_model_id),
                ('res_id', '=', self.id),
                ('user_id', '=', user.id),
                ('summary', 'like', 'HR Validate KHTN'),
            ], limit=1)
            if not existing:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': res_model_id,
                    'res_id': self.id,
                    'user_id': user.id,
                    'summary': _('HR Validate KHTN: %s') % self.name,
                    'note': _('Tất cả Trưởng phòng đã duyệt kế hoạch tuyển dụng %s. Vui lòng kiểm tra và validate.') % self.name,
                    'activity_type_id': activity_type.id if activity_type else False,
                    'date_deadline': fields.Date.today(),
                })

    def _send_activity_to_ceo_for_approval(self):
        """Gửi Activity cho CEO (company.user_id) khi HR đã validate xong"""
        self.ensure_one()
        ceo_user = self.company_id.ceo_id.user_id if self.company_id.ceo_id else False
        if not ceo_user:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        res_model_id = self.env['ir.model']._get_id('recruitment.plan')
        existing = self.env['mail.activity'].sudo().search([
            ('res_model_id', '=', res_model_id),
            ('res_id', '=', self.id),
            ('user_id', '=', ceo_user.id),
            ('summary', 'like', 'CEO duyệt KHTN'),
        ], limit=1)
        if not existing:
            self.env['mail.activity'].sudo().create({
                'res_model_id': res_model_id,
                'res_id': self.id,
                'user_id': ceo_user.id,
                'summary': _('CEO duyệt KHTN: %s') % self.name,
                'note': _('HR đã validate kế hoạch tuyển dụng %s. Vui lòng xem xét và phê duyệt.') % self.name,
                'activity_type_id': activity_type.id if activity_type else False,
                'date_deadline': fields.Date.today(),
            })

    def action_hr_validate(self):
        self.with_context(skip_parent_sync=True).write({'state': 'waiting_ceo'})
        self.line_ids.write({'state': 'waiting_ceo'})
        if not self.is_sub_plan:
            # Parent plan: cập nhật tất cả sub-plans sang waiting_ceo và gửi activity CEO
            self.sub_plan_ids.with_context(skip_parent_sync=True).write({'state': 'waiting_ceo'})
            self.sub_plan_ids.mapped('line_ids').write({'state': 'waiting_ceo'})
            self._send_activity_to_ceo_for_approval()
        elif self.parent_id:
            # Cập nhật dòng tương ứng trong parent
            if self.department_id:
                self.parent_id.line_ids.filtered(
                    lambda l: l.department_id == self.department_id
                ).write({'state': 'waiting_ceo'})
            # Nếu tất cả subs đã waiting_ceo thì cập nhật parent và gửi activity CEO
            all_subs_hr = all(s.state == 'waiting_ceo' for s in self.parent_id.sub_plan_ids)
            if all_subs_hr:
                self.parent_id.with_context(skip_parent_sync=True).write({'state': 'waiting_ceo'})
                self.parent_id._send_activity_to_ceo_for_approval()

    def action_ceo_approve(self):
        self.with_context(skip_parent_sync=True).write({'state': 'in_progress'})
        self.line_ids.write({'state': 'in_progress'})
        if not self.is_sub_plan:
            # Parent plan: cập nhật tất cả sub-plans xuống in_progress
            self.sub_plan_ids.with_context(skip_parent_sync=True).write({'state': 'in_progress'})
            self.sub_plan_ids.mapped('line_ids').write({'state': 'in_progress'})
        elif self.parent_id:
            # Cập nhật dòng tương ứng trong parent
            if self.department_id:
                self.parent_id.line_ids.filtered(
                    lambda l: l.department_id == self.department_id
                ).write({'state': 'in_progress'})
            all_subs_ceo = all(s.state == 'in_progress' for s in self.parent_id.sub_plan_ids)
            if all_subs_ceo:
                self.parent_id.with_context(skip_parent_sync=True).write({'state': 'in_progress'})

    def action_publish_jobs(self):
        """Update Job Positions and Publish them"""
        self.ensure_one()
        published_count = 0
        for line in self.line_ids:
            # Only process lines that haven't been published yet
            if line.job_id and not line.is_published:
                job = line.job_id
                # Update Quantity and Publish
                # Note: Odoo 19 uses website_published for recruitment
                job.sudo().write({
                    'no_of_recruitment': job.no_of_recruitment + line.quantity,
                    'website_published': True, 
                    'active': True,
                })
                # Mark as published to avoid duplicate increments
                line.is_published = True
                published_count += 1

        message = f'Đã cập nhật {published_count} vị trí và đăng tin lên Portal tuyển dụng.'
        if published_count == 0:
            message = 'Tất cả vị trí trong kế hoạch này đã được đăng bộ từ trước.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thông báo',
                'message': message,
                'sticky': False,
                'type': 'success' if published_count > 0 else 'warning',
                'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
            }
        }

    def action_confirm(self):
        # Deprecated or Alias for Submit
        self.action_submit()

    def action_done(self):
        self.ensure_one()
        if self.sub_plan_ids:
            # Parent plan: tất cả sub-plans phải done trước
            not_done = self.sub_plan_ids.filtered(lambda s: s.state != 'done')
            if not_done:
                names = ", ".join(not_done.mapped('name'))
                raise exceptions.UserError(
                    _("Còn %d kế hoạch con chưa hoàn thành: %s")
                    % (len(not_done), names)
                )
        else:
            # Sub-plan hoặc standalone: phải tuyển đủ người
            unfilled = self.line_ids.filtered(lambda l: l.hired_count < l.quantity)
            if unfilled:
                details = ", ".join(
                    _("%s (%d/%d)") % (l.job_id.name, l.hired_count, l.quantity)
                    for l in unfilled
                )
                raise exceptions.UserError(
                    _("Chưa tuyển đủ người cho các vị trí sau: %s") % details
                )
        self.write({'state': 'done'})
        self.line_ids.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.line_ids.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
        self.line_ids.write({'state': 'draft'})

    def action_open_job_page(self):
        """Open the standard Odoo job page on website"""
        self.ensure_one()
        url = '/jobs'
        if len(self.line_ids) == 1:
            job = self.line_ids[0].job_id
            job_url = job.website_url if job and hasattr(job, 'website_url') else False
            if job_url:
                url = job_url
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    # === Cron Methods ===
    @api.model
    def _cron_remind_manager(self):
        """Cron to remind managers after 1 minute (for test) if not approved"""
        from datetime import datetime, timedelta
        deadline = datetime.now() - timedelta(minutes=1)
        plans = self.search([
            ('state', '=', 'waiting_manager'),
            ('date_submitted', '<=', deadline),
            ('is_reminder_sent', '=', False)
        ])
        for plan in plans:
            # Send Email Notification
            plan._notify_department_heads()
            plan.message_post(body="Hệ thống tự động nhắc nhở: Kế hoạch này đã quá hạn duyệt.")
            plan.is_reminder_sent = True

    @api.model
    def _cron_check_monthly_notification(self):
        """Cron to notify when the planned month arrives"""
        from datetime import timedelta
        today = fields.Date.today()
        # Find lines in 'in_progress' plans where planned_date is this month
        lines = self.env['recruitment.plan.line'].search([
            ('plan_id.state', '=', 'in_progress'),
            ('planned_date', '>=', today.replace(day=1)),
            ('planned_date', '<', (today + timedelta(days=31)).replace(day=1))
        ])
        for line in lines:
            # Notify HR/Managers
            msg = f"Thông báo: Vị trí {line.job_id.name} dự kiến tuyển dụng trong tháng này ({line.planned_date})."
            line.plan_id.message_post(body=msg)


class RecruitmentPlanLine(models.Model):
    _name = 'recruitment.plan.line'
    _description = 'Chi tiết Kế Hoạch Tuyển Dụng'

    plan_id = fields.Many2one('recruitment.plan', string='Kế hoạch', required=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', string='Phòng ban', required=True)
    job_id = fields.Many2one('hr.job', string='Vị trí', required=True)
    quantity = fields.Integer(string='Số lượng cần', default=1, required=True)
    planned_date = fields.Date(string='Thời gian dự kiến', required=True)
    reason = fields.Text(string='Ghi chú')
    is_approved = fields.Boolean(
        string='Duyệt', default=True,
        help='Tích ✓ = giữ lại, bỏ tích ✗ = loại khi Trưởng bộ phận duyệt')
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('waiting_manager', 'Chờ Line Manager duyệt'),
        ('manager_approved', 'Manager đã duyệt'),
        ('hr_validation', 'HR Validate'),
        ('waiting_ceo', 'Chờ CEO duyệt'),
        ('in_progress', 'Đang tuyển'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft')
    
    batch_id = fields.Many2one('recruitment.batch', string='Đợt tuyển dụng', ondelete='set null')

    # === Progress Metrics (Funnel 1-35) ===
    applicant_count = fields.Integer(compute='_compute_metrics', string='Ứng viên')
    interview_count = fields.Integer(compute='_compute_metrics', string='Phỏng vấn')
    hired_count = fields.Integer(compute='_compute_metrics', string='Trúng tuyển')
    is_published = fields.Boolean(string='Đã đăng Portal', default=False, copy=False)

    def _compute_metrics(self):
        for line in self:
            # Note: We filter by job and department as defined in the line
            domain = [
                ('job_id', '=', line.job_id.id),
                ('department_id', '=', line.department_id.id),
            ]
            applicants = self.env['hr.applicant'].sudo().search(domain)
            line.applicant_count = len(applicants)
            # Interviews: typically applicants in 'Interview' stages
            line.interview_count = len(applicants.filtered(lambda a: 'interview' in (a.stage_id.name or '').lower()))
            # Hired: typically applicants in 'Contract Signed' or similar stage
            line.hired_count = len(applicants.filtered(lambda a: a.date_closed or 'hired' in (a.stage_id.name or '').lower()))


class RecruitmentBatch(models.Model):
    _name = 'recruitment.batch'
    _description = 'Đợt Tuyển Dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Mã đợt', required=True, copy=False, readonly=True,
        default=lambda self: 'New')

    batch_name = fields.Char(
        string='Tên đợt tuyển dụng', required=True, tracking=True,
        help='Ví dụ: Đợt Tuyển Dụng Quý 1/2025')

    date_start = fields.Date(string='Ngày bắt đầu', tracking=True)
    date_end = fields.Date(string='Ngày kết thúc', tracking=True)

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('open', 'Đang mở'),
        ('waiting_ceo', 'Chờ CEO duyệt'),
        ('approved', 'CEO đã duyệt'),
        ('closed', 'Đã đóng'),
    ], string='Trạng thái', default='draft', tracking=True)

    line_ids = fields.One2many('recruitment.plan.line', 'batch_id', string='Các vị trí trong đợt')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                code = 'recruitment.batch'
                seq = self.env['ir.sequence'].next_by_code(code)
                if not seq:
                    seq_obj = self.env['ir.sequence'].sudo().search([('code', '=', code)], limit=1)
                    if not seq_obj:
                        seq_obj = self.env['ir.sequence'].sudo().create({
                            'name': 'Recruitment Batch',
                            'code': code,
                            'prefix': 'BATCH/%(year)s/',
                            'padding': 4,
                            'company_id': False,
                        })
                    seq = seq_obj.next_by_id()
                vals['name'] = seq or 'New'
        return super(RecruitmentBatch, self).create(vals_list)

    def action_open_batch(self):
        self.write({'state': 'open'})

    def action_send_ceo(self):
        self.ensure_one()
        if not self.line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Cảnh báo',
                    'message': 'Đợt tuyển dụng chưa có vị trí nào. Vui lòng kéo các vị trí đã duyệt vào.',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        self.write({'state': 'waiting_ceo'})
        
        # Propagate to associated Plans, their parents AND their sub-plans
        plans = self.line_ids.mapped('plan_id')
        for plan in plans:
            target_state = 'waiting_ceo'
            # Update plan itself
            plan.write({'state': target_state})
            # Update all sub-plans of this plan (important!)
            if plan.sub_plan_ids:
                plan.sub_plan_ids.write({'state': target_state})
            # Update parent plan (if this is a sub-plan)
            if plan.parent_id:
                plan.parent_id.write({'state': target_state})
                # Bonus: update all siblings of this plan to keep everything in sync
                if plan.parent_id.sub_plan_ids:
                    plan.parent_id.sub_plan_ids.write({'state': target_state})

    def action_ceo_approve_batch(self):
        self.write({'state': 'approved'})
        
        # Transition associated plans and all related plans to 'in_progress'
        plans = self.line_ids.mapped('plan_id')
        target_state = 'in_progress'
        for plan in plans:
            plan.write({'state': target_state})
            if plan.sub_plan_ids:
                plan.sub_plan_ids.write({'state': target_state})
            if plan.parent_id:
                plan.parent_id.write({'state': target_state})
                if plan.parent_id.sub_plan_ids:
                    plan.parent_id.sub_plan_ids.write({'state': target_state})

        # Update lines states in batch
        self.line_ids.write({'state': 'recruiting'})

    def action_ceo_reject_batch(self):
        self.write({'state': 'open'})
        # Revert associated plans and related to 'manager_approved'
        plans = self.line_ids.mapped('plan_id')
        target_state = 'manager_approved'
        for plan in plans:
            plan.write({'state': target_state})
            if plan.sub_plan_ids:
                plan.sub_plan_ids.write({'state': target_state})
            if plan.parent_id:
                plan.parent_id.write({'state': target_state})
                if plan.parent_id.sub_plan_ids:
                    plan.parent_id.sub_plan_ids.write({'state': target_state})

    def action_close(self):
        self.write({'state': 'closed'})
        self.line_ids.write({'state': 'done'})

    def action_reopen(self):
        self.write({'state': 'open'})

    def action_view_applicants(self):
        self.ensure_one()
        job_ids = self.line_ids.mapped('job_id').ids
        return {
            'name': _('Ứng viên trong đợt'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'list,form,kanban',
            'domain': [('job_id', 'in', job_ids)],
            'context': {
                'default_job_id': job_ids[0] if job_ids else False,
            },
            'target': 'current',
        }

    def action_pull_approved_lines(self):
        """Kéo tất cả các vị trí đã được Manager duyệt và chưa thuộc đợt nào"""
        self.ensure_one()
        lines = self.env['recruitment.plan.line'].search([
            ('plan_id.state', 'in', ['manager_approved', 'hr_validation', 'waiting_ceo', 'ceo_approval', 'in_progress']),
            ('batch_id', '=', False)
        ])
        if not lines:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': 'Không có vị trí đã duyệt nào khả dụng để kéo vào.',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        lines.write({'batch_id': self.id})
        lines.write({'state': 'waiting'})
        
        # Propagate to associated Plans: move to 'hr_validation'
        plans = lines.mapped('plan_id')
        target_state = 'hr_validation'
        for plan in plans:
            plan.write({'state': target_state})
            if plan.sub_plan_ids:
                plan.sub_plan_ids.write({'state': target_state})
            if plan.parent_id:
                plan.parent_id.write({'state': target_state})
                if plan.parent_id.sub_plan_ids:
                    plan.parent_id.sub_plan_ids.write({'state': target_state})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã kéo {len(lines)} vị trí vào đợt tuyển dụng này và cập nhật trạng thái Kế hoạch sang HR Validate.',
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
            }
        }

    @api.model
    def _cron_auto_publish_approved_batches(self):
        """
        Cron to check approved batches whose start date has arrived.
        If today >= date_start, publish jobs and notify.
        """
        today = fields.Date.today()
        # Find approved batches that should start
        batches = self.search([
            ('state', '=', 'approved'),
            ('date_start', '<=', today)
        ])
        
        for batch in batches:
            # 1. Update batch state to 'open' (or keep approved? user said 'bắt đầu tuyển rồi' 
            # so it should be in progress/open). Let's use 'open'.
            batch.write({'state': 'open'})
            
            # 2. Get all associated plans and sub-plans
            plans = batch.line_ids.mapped('plan_id')
            all_related_plans = plans | plans.mapped('sub_plan_ids') | plans.mapped('parent_id')
            
            # 3. Transition plans to 'in_progress' and publish jobs
            for plan in all_related_plans.filtered(lambda p: p.state == 'in_progress'):
                plan.action_publish_jobs()
                
                # 4. Notify department heads
                involved_depts = plan.line_ids.mapped('department_id')
                dept_names = ", ".join(involved_depts.mapped('name'))
                msg = f"🔔 Thông báo: Đợt tuyển dụng '{batch.batch_name}' đã chính thức bắt đầu hôm nay ({today}). " \
                      f"Vị trí tuyển dụng của các phòng ban [{dept_names}] đã được đăng tin lên Portal."
                plan.message_post(body=msg)
            
            batch.message_post(body=f"Hệ thống tự động kích hoạt đợt tuyển dụng này vì đã đến ngày bắt đầu ({batch.date_start}).")


class HrApplicantInherit(models.Model):
    _inherit = 'hr.applicant'

    application_source = fields.Selection([
        ('web', 'Website (Portal)'),
        ('api', 'API / Hệ thống bên ngoài'),
        ('manual', 'HR tạo thủ công'),
        ('website', 'Website Công ty'),
        ('topcv', 'TopCV'),
        ('vietnamworks', 'VietnamWorks'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Giới thiệu'),
        ('other', 'Nguồn khác'),
    ], string='Nguồn ứng viên', default='other', tracking=True)
