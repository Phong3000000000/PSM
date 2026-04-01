# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PayrollOpsConfig(models.Model):
    """
    Singleton configuration model for M02_P0207_02 payroll workflow.
    Stores who approves/receives notifications at each payroll step.
    """
    _name = 'payroll.ops.config'
    _description = 'Payroll OPS Configuration'

    name = fields.Char(default='Payroll OPS Config', readonly=True)

    # ── C-Level: ai duyệt Payment Authorization ─────────────────────────────
    clevel_approver_ids = fields.Many2many(
        'res.users',
        'payroll_ops_config_clevel_rel',
        'config_id', 'user_id',
        string='C-Level Approvers',
        help='Danh sách người phê duyệt Payment Authorization (C-Level).',
    )

    # ── C&B: ai được thông báo khi payslip bị từ chối ───────────────────────
    cb_notify_ids = fields.Many2many(
        'res.users',
        'payroll_ops_config_cb_rel',
        'config_id', 'user_id',
        string='C&B Notification Recipients',
        help='Những người nhận thông báo khi phiếu lương bị HR từ chối.',
    )

    # ── Finance: ai nhận UNC sau khi C-Level duyệt ──────────────────────────
    finance_notify_ids = fields.Many2many(
        'res.users',
        'payroll_ops_config_finance_rel',
        'config_id', 'user_id',
        string='Finance Recipients',
        help='Những người nhận thông báo UNC khi C-Level duyệt Payment Authorization.',
    )

    @api.model
    def get_config(self):
        """Return the singleton config record, creating one if it doesn't exist."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Payroll OPS Config'})
        return config
