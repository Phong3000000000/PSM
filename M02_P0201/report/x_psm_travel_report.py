from odoo import api, fields, models

class TravelAnalysisReport(models.Model):
    _name = 'x_psm_travel_analysis_report'
    _description = 'Travel Analysis Report'
    _auto = False
    _rec_name = 'x_psm_name'
    _order = 'x_psm_date_start desc'

    x_psm_name = fields.Char(string='Reference', readonly=True)
    x_psm_employee_id = fields.Many2one('hr.employee', string='Requester', readonly=True)
    x_psm_department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    x_psm_date_start = fields.Date(string='Start Date', readonly=True)
    x_psm_date_end = fields.Date(string='End Date', readonly=True)
    x_psm_destination_id = fields.Many2one('x_psm_travel_destination', string='Destination', readonly=True)
    x_psm_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('refused', 'Refused')
    ], string='Status', readonly=True)
    x_psm_budget_hotel = fields.Float(string='Hotel Budget', readonly=True)
    x_psm_budget_allowance = fields.Float(string='Allowance Budget', readonly=True)
    x_psm_budget_total = fields.Float(string='Total Budget', readonly=True)
    x_psm_overnight_count = fields.Integer(string='Overnights', readonly=True)
    x_psm_duration_days = fields.Integer(string='Duration (Days)', readonly=True)
    x_psm_company_id = fields.Many2one('res.company', string='Company', readonly=True)
    x_psm_nbr = fields.Integer(string='Number of Requests', readonly=True)

    @property
    def _table_query(self):
        return """
            SELECT
                tr.id AS id,
                tr.x_psm_name AS x_psm_name,
                tr.x_psm_employee_id AS x_psm_employee_id,
                tr.x_psm_department_id AS x_psm_department_id,
                tr.x_psm_date_start AS x_psm_date_start,
                tr.x_psm_date_end AS x_psm_date_end,
                tr.x_psm_destination_id AS x_psm_destination_id,
                tr.x_psm_state AS x_psm_state,
                tr.x_psm_budget_hotel AS x_psm_budget_hotel,
                tr.x_psm_budget_allowance AS x_psm_budget_allowance,
                tr.x_psm_budget_total AS x_psm_budget_total,
                tr.x_psm_overnight_count AS x_psm_overnight_count,
                tr.x_psm_duration_days AS x_psm_duration_days,
                he.company_id AS x_psm_company_id,
                1 AS x_psm_nbr
            FROM x_psm_travel_request tr
                LEFT JOIN hr_employee he ON he.id = tr.x_psm_employee_id
        """
