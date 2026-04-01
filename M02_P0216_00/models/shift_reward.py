from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessError
import datetime

class ShiftReward(models.Model):
    _name = 'shift.reward'
    _description = 'Employee Reward'
    _order = 'date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Tên',
        compute='_compute_name',
        store=True
    )
    date = fields.Date(
        string='Tháng/Ngày',
        required=True,
        default=fields.Date.context_today
    )
    reward_type = fields.Selection([
        ('eotm', 'EOTM (Nhân viên xuất sắc tháng)'),
        ('eotq', 'EOTQ (Nhân viên xuất sắc quý)'),
    ], string='Loại khen thưởng', required=True, default='eotm')
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên tiêu biểu',
        readonly=True
    )
    score = fields.Float(
        string='Điểm trung bình',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    reward_line_ids = fields.One2many(
        'shift.reward.line',
        'reward_id',
        string='Bảng điểm chi tiết'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Chi nhánh',
        required=True,
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ShiftReward, self).create(vals_list)
        for record in records:
            if record.state == 'draft':
                record._calculate_scores()
        return records

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        """Tự động kiểm tra và tạo bản ghi khi người dùng truy cập danh sách"""
        if not self.env.context.get('disable_generation'):
            self.with_context(disable_generation=True)._generate_missing_rewards()
        
        if count:
            return self.search_count(domain)
            
        return super(ShiftReward, self).search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def _generate_missing_rewards(self):
        """
        Quét tất cả Shift Evaluation (Đánh giá ca) có trong hệ thống để tạo Reward (EOTM/EOTQ) tương ứng.
        Dựa trên dữ liệu thực tế thay vì chỉ tạo cho thời gian hiện tại.
        """
        # 1. Tìm tất cả các cặp (tháng, chi nhánh) có đánh giá hợp lệ
        # Sử dụng SQL trực tiếp để gom nhóm nhanh chóng và chính xác
        self.env.cr.execute("""
            SELECT DISTINCT 
                date_trunc('month', date)::date as month_start,
                company_id
            FROM shift_evaluation
            WHERE state != 'cancelled' AND date IS NOT NULL AND company_id IS NOT NULL
            ORDER BY month_start DESC
        """)
        results = self.env.cr.dictfetchall()

        for res in results:
            month_start = res['month_start']
            company_id = res['company_id']
            
            # --- Xử lý EOTM (Tháng) ---
            eotm_exist = self.search([
                ('reward_type', '=', 'eotm'),
                ('date', '>=', month_start),
                ('date', '<', month_start + relativedelta(months=1)),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not eotm_exist:
                # Tạo EOTM vào ngày cuối tháng đó
                create_date = month_start + relativedelta(months=1, days=-1)
                self.create({
                    'reward_type': 'eotm',
                    'date': create_date,
                    'company_id': company_id
                })
            elif eotm_exist.state == 'draft':
                 eotm_exist._calculate_scores()

            # --- Xử lý EOTQ (Quý) ---
            # Xác định quý của tháng đó
            quarter = (month_start.month - 1) // 3 + 1
            q_start_month = (quarter - 1) * 3 + 1
            quarter_start = datetime.date(month_start.year, q_start_month, 1)
            
            # Kiểm tra xem có EOTQ cho quý này chưa
            eotq_exist = self.search([
                ('reward_type', '=', 'eotq'),
                ('date', '>=', quarter_start),
                ('date', '<', quarter_start + relativedelta(months=3)),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not eotq_exist:
                # Tạo EOTQ vào ngày cuối quý
                create_date = quarter_start + relativedelta(months=3, days=-1)
                self.create({
                    'reward_type': 'eotq',
                    'date': create_date,
                    'company_id': company_id
                })
            elif eotq_exist.state == 'draft':
                eotq_exist._calculate_scores()

    @api.depends('date', 'reward_type', 'company_id')
    def _compute_name(self):
        for record in self:
            if not record.date or not record.reward_type:
                record.name = _("Mới")
                continue
            
            type_label = "EOTM" if record.reward_type == 'eotm' else "EOTQ"
            if record.reward_type == 'eotm':
                date_str = record.date.strftime('%m/%Y')
            else:
                quarter = (record.date.month - 1) // 3 + 1
                date_str = f"Q{quarter}/{record.date.year}"
            
            company_code = record.company_id.name or ""
            record.name = f"{type_label} - {date_str} - {company_code}"

    @api.onchange('date', 'reward_type', 'company_id')
    def _onchange_calculate(self):
        """Tự động tính toán khi thay đổi trên giao diện"""
        self._calculate_scores()

    def _calculate_scores(self):
        """Hàm lõi tính toán điểm trung bình và tìm người chiến thắng"""
        for record in self:
            if not record.date or not record.reward_type or record.state == 'confirmed':
                continue

            start_date, end_date = record._get_period_dates()
            
            # Ensure we have a valid company ID, handling both integer and recordset cases for robustness
            current_company_id = record.company_id.id if record.company_id else False
            if not current_company_id:
                 continue

            # Lấy tất cả điểm post.shift trong khoảng thời gian VÀ cùng chi nhánh
            post_shifts = self.env['post.shift'].search([
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('shift_evaluation_id.company_id', '=', current_company_id)
            ])
            
            if not post_shifts:
                record.reward_line_ids = [(5, 0, 0)]
                record.employee_id = False
                record.score = 0.0
                continue

            # Gom nhóm theo nhân viên và tính trung bình
            employee_scores = {}
            for ps in post_shifts:
                if ps.employee_id not in employee_scores:
                    employee_scores[ps.employee_id] = []
                employee_scores[ps.employee_id].append(ps.score)

            avg_scores = []
            for employee, scores in employee_scores.items():
                avg = sum(scores) / len(scores) if scores else 0.0
                avg_scores.append({
                    'employee_id': employee.id,
                    'average_score': avg
                })

            # Sắp xếp để tìm người cao nhất
            avg_scores.sort(key=lambda x: x['average_score'], reverse=True)

            # Cập nhật lines
            record.reward_line_ids = [(5, 0, 0)]  # Xóa cũ
            line_commands = [(0, 0, val) for val in avg_scores]
            record.reward_line_ids = line_commands

            # Cập nhật winner
            if avg_scores:
                record.employee_id = avg_scores[0]['employee_id']
                record.score = avg_scores[0]['average_score']
            else:
                record.employee_id = False
                record.score = 0.0

    def _get_period_dates(self):
        """Helper để lấy ngày bắt đầu/kết thúc tháng hoặc quý"""
        d = self.date
        if self.reward_type == 'eotm':
            start_date = d.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        else:
            quarter = (d.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = datetime.date(d.year, start_month, 1)
            end_date = start_date + relativedelta(months=3, days=-1)
        return start_date, end_date

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        # Send email to the winner
        for record in self:
            if record.employee_id and record.employee_id.work_email:
                template = self.env.ref('M02_P0216_00.mail_template_shift_reward_winner', raise_if_not_found=False)
                if template:
                    email_values = {'email_to': record.employee_id.work_email}
                    template.send_mail(record.id, force_send=True, email_values=email_values)

    def action_draft(self):
        self.write({'state': 'draft'})


    def action_grant_points(self):
        """Cấp điểm cho người chiến thắng thông qua Point Grant"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_("Vui lòng xác nhận trước khi cấp điểm."))
            
            if not record.employee_id:
                raise UserError(_("Chưa có người chiến thắng để cấp điểm."))
            
            # Determine fund type based on reward type
            fund_type = 'EOTM' if record.reward_type == 'eotm' else 'EOTQ'
            
            # 1. Find Fund
            fund = self.env['shift.point.fund'].search([('fund_type', '=', fund_type)], limit=1)
            if not fund:
                raise UserError(_("Không tìm thấy kho điểm %s!") % fund_type)
            
            point_to_grant = 100
            
            # 2. Create Point Grant
            # Using action_confirm of point.grant handles the fund check and balance update
            grant = self.env['point.grant'].create({
                'employee_id': record.employee_id.id,
                'fund_id': fund.id,
                'points': point_to_grant,
                'reason': record.name or _('Thưởng %s') % fund_type,
                'date': fields.Date.today(),
            })
            
            # 3. Confirm Grant (This deducts fund and adds to employee)
            grant.action_confirm()
            
            # 4. Update Winner Line
            winner_line = record.reward_line_ids.filtered(lambda l: l.employee_id == record.employee_id)
            if winner_line:
                winner_line.write({'reward_point': point_to_grant})
            
            # Optional: Log note
            self.message_post(body=_("Đã cấp %s điểm cho nhân viên xuất sắc %s thông qua phiếu %s.") % (point_to_grant, record.employee_id.name, grant.name))
            
            record.is_granted = True

    is_granted = fields.Boolean(string='Đã cấp điểm', default=False, copy=False)

    def _check_rgm_access(self):
        """Kiểm tra user có phải Regional General Manager không"""
        if not self.env.user.has_group('your_module_name.group_regional_general_manager'):
            # Hoặc kiểm tra qua job position
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            if not employee or employee.job_id.name != 'Regional General Manager':
                raise AccessError(_("Chỉ Regional General Manager mới có quyền thực hiện thao tác này!"))

    # @api.model_create_multi
    # def create(self, vals_list):
    #     self._check_rgm_access()
    #     return super(ShiftReward, self).create(vals_list)

    # def write(self, vals):
    #     self._check_rgm_access()
    #     return super(ShiftReward, self).write(vals)

    # def unlink(self):
    #     self._check_rgm_access()
    #     return super(ShiftReward, self).unlink()

    # def action_confirm(self):
    #     self._check_rgm_access()
    #     return super(ShiftReward, self).action_confirm()

    # def action_grant_points(self):
    #     self._check_rgm_access()
    #     return super(ShiftReward, self).action_grant_points()


class ShiftRewardLine(models.Model):
    _name = 'shift.reward.line'
    _description = 'Reward Detailed Score'
    _order = 'average_score desc'

    reward_id = fields.Many2one('shift.reward', string='Khen thưởng', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    average_score = fields.Float(string='Điểm trung bình')
    reward_point = fields.Float(string='Điểm thưởng')
