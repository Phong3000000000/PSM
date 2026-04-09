# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from markupsafe import escape


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    x_psm_0205_recruitment_request_id = fields.Many2one(
        "x_psm_recruitment_request",
        string="Yêu cầu tuyển dụng",
        copy=False,
        index=True,
        ondelete="set null",
    )
    x_psm_0205_request_code = fields.Char(
        related="x_psm_0205_recruitment_request_id.name",
        string="Mã yêu cầu",
        readonly=True,
    )
    x_psm_0205_request_owner_id = fields.Many2one(
        "res.users",
        related="x_psm_0205_recruitment_request_id.user_id",
        string="Người yêu cầu",
        readonly=True,
    )
    x_psm_0205_department_id = fields.Many2one(
        "hr.department",
        related="x_psm_0205_recruitment_request_id.department_id",
        string="Phòng ban",
        readonly=True,
    )
    x_psm_0205_request_type = fields.Selection(
        related="x_psm_0205_recruitment_request_id.request_type",
        string="Loại yêu cầu",
        readonly=True,
    )
    x_psm_0205_recruitment_block = fields.Selection(
        related="x_psm_0205_recruitment_request_id.recruitment_block",
        string="Khối tuyển dụng",
        readonly=True,
    )
    x_psm_0205_reason = fields.Text(
        related="x_psm_0205_recruitment_request_id.reason",
        string="Lý do",
        readonly=True,
    )
    x_psm_0205_request_line_ids = fields.One2many(
        related="x_psm_0205_recruitment_request_id.line_ids",
        string="Danh sách tuyển dụng",
        readonly=True,
    )
    x_psm_0205_total_quantity = fields.Integer(
        string="Tổng số vị trí",
        compute="_compute_x_psm_0205_total_quantity",
        readonly=True,
    )
    x_psm_0205_request_line_count = fields.Integer(
        string="Số dòng tuyển dụng",
        compute="_compute_x_psm_0205_total_quantity",
        readonly=True,
    )
    x_psm_0205_has_request_lines = fields.Boolean(
        string="Có dòng tuyển dụng",
        compute="_compute_x_psm_0205_detail_fallback",
        readonly=True,
    )
    x_psm_0205_detail_fallback_html = fields.Html(
        string="Chi tiết fallback",
        compute="_compute_x_psm_0205_detail_fallback",
        sanitize=True,
        readonly=True,
    )

    @api.depends(
        "x_psm_0205_recruitment_request_id.quantity",
        "x_psm_0205_recruitment_request_id.line_ids.quantity",
        "x_psm_0205_recruitment_request_id.request_type",
    )
    def _compute_x_psm_0205_total_quantity(self):
        for request in self:
            recruitment_request = request.x_psm_0205_recruitment_request_id
            if not recruitment_request:
                request.x_psm_0205_total_quantity = 0
                request.x_psm_0205_request_line_count = 0
                continue
            if recruitment_request.line_ids:
                request.x_psm_0205_total_quantity = sum(recruitment_request.line_ids.mapped("quantity"))
                request.x_psm_0205_request_line_count = len(recruitment_request.line_ids)
            else:
                request.x_psm_0205_total_quantity = recruitment_request.quantity or 0
                request.x_psm_0205_request_line_count = 1 if recruitment_request.job_id else 0

    @api.depends(
        "x_psm_0205_recruitment_request_id",
        "x_psm_0205_recruitment_request_id.line_ids",
        "x_psm_0205_recruitment_request_id.job_id",
        "x_psm_0205_recruitment_request_id.quantity",
        "x_psm_0205_recruitment_request_id.reason",
        "x_psm_0205_recruitment_request_id.department_id",
        "x_psm_0205_recruitment_request_id.recruitment_block",
    )
    def _compute_x_psm_0205_detail_fallback(self):
        for request in self:
            recruitment_request = request.x_psm_0205_recruitment_request_id
            request.x_psm_0205_has_request_lines = bool(recruitment_request and recruitment_request.line_ids)
            request.x_psm_0205_detail_fallback_html = False
            if not recruitment_request or recruitment_request.line_ids:
                continue

            job = recruitment_request.job_id
            position_name = job.display_name if job else "-"

            position_level_label = "-"
            if job and "position_level" in job._fields and job.position_level:
                level_selection = dict(job._fields["position_level"].selection)
                position_level_label = level_selection.get(job.position_level, job.position_level)

            location_name = "-"
            if job and "work_location_id" in job._fields and job.work_location_id:
                location_name = job.work_location_id.display_name

            recruitment_block_label = dict(
                recruitment_request._fields["recruitment_block"].selection
            ).get(recruitment_request.recruitment_block, recruitment_request.recruitment_block or "-")

            department_name = recruitment_request.department_id.display_name or "-"
            quantity = recruitment_request.quantity or 0
            reason = recruitment_request.reason or "-"
            reason_html = escape(reason).replace("\n", "<br/>")

            request.x_psm_0205_detail_fallback_html = (
                "<table class='table table-sm table-hover o_list_table mb-0'>"
                "<thead>"
                "<tr>"
                "<th>Vị trí tuyển dụng</th>"
                "<th>Cấp bậc</th>"
                "<th>Job Location</th>"
                "<th>Khối tuyển dụng</th>"
                "<th>Phòng ban</th>"
                "<th>Số lượng</th>"
                "<th>Ghi chú/Mô tả</th>"
                "</tr>"
                "</thead>"
                "<tbody>"
                "<tr>"
                f"<td>{escape(position_name)}</td>"
                f"<td>{escape(position_level_label or '-')}</td>"
                f"<td>{escape(location_name or '-')}</td>"
                f"<td>{escape(recruitment_block_label or '-')}</td>"
                f"<td>{escape(department_name)}</td>"
                f"<td>{escape(str(quantity))}</td>"
                f"<td>{reason_html}</td>"
                "</tr>"
                "</tbody>"
                "</table>"
            )

    def action_open_psm_recruitment_request(self):
        self.ensure_one()
        if not self.x_psm_0205_recruitment_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Yêu Cầu Tuyển Dụng"),
            "res_model": "x_psm_recruitment_request",
            "view_mode": "form",
            "res_id": self.x_psm_0205_recruitment_request_id.id,
            "target": "current",
        }

    @api.depends("approver_ids.status", "approver_ids.required")
    def _compute_request_status(self):
        super()._compute_request_status()
        linked_requests = self.mapped("x_psm_0205_recruitment_request_id")
        if linked_requests:
            linked_requests._sync_state_from_approval_requests()
