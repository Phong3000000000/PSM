# -*- coding: utf-8 -*-
from odoo import models, fields


class HrDisciplineExplanation(models.Model):
    _name = "hr.discipline.explanation"
    _description = "Discipline Explanation Entry"
    _order = "create_date desc"

    record_id = fields.Many2one(
        "hr.discipline.record",
        string="Discipline Record",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Lần thứ", default=1)

    # Explanation content
    incident_date_time = fields.Datetime(string="Thời gian xảy ra sự việc")
    incident_location = fields.Char(string="Địa điểm")
    witness_names = fields.Char(string="Người làm chứng")
    explanation_content = fields.Text(string="Nội dung tường trình")
    explanation_reason = fields.Text(string="Nguyên nhân")
    explanation_commitment = fields.Text(string="Cam kết")
    employee_signature = fields.Binary(string="Chữ ký")

    # Status
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("rejected", "Rejected"),
            ("accepted", "Accepted"),
        ],
        default="draft",
        string="Trạng thái",
    )

    rejection_reason = fields.Text(string="Lý do từ chối")
    submitted_date = fields.Datetime(string="Ngày gửi")
    reviewed_date = fields.Datetime(string="Ngày review")
    reviewed_by = fields.Many2one("res.users", string="Người review")
