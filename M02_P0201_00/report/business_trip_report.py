from odoo import api, fields, models


class BusinessTripReport(models.Model):
    _name = 'business.trip.report'
    _description = 'Business Trip Analysis Report'
    _auto = False
    _rec_name = 'name'
    _order = 'date_start desc'

    name = fields.Char(string="Tên yêu cầu", readonly=True)
    create_date = fields.Datetime(string="Ngày tạo", readonly=True)
    date_start = fields.Datetime(string="Ngày bắt đầu", readonly=True)
    date_end = fields.Datetime(string="Ngày kết thúc", readonly=True)
    request_owner_id = fields.Many2one(
        'res.users', string="Người yêu cầu", readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', string="Nhân viên", readonly=True)
    department_id = fields.Many2one(
        'hr.department', string="Phòng ban", readonly=True)
    category_id = fields.Many2one(
        'approval.category', string="Loại phê duyệt", readonly=True)
    destination_province_id = fields.Many2one(
        'travel.province', string="Tỉnh/TP đích", readonly=True)
    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Canceled'),
        ('completed', 'Completed'),
    ], string="Trạng thái", readonly=True)
    company_id = fields.Many2one(
        'res.company', string="Công ty", readonly=True)
    estimated_hotel_cost = fields.Float(
        string="Chi phí khách sạn ước tính", readonly=True)
    hotel_nights = fields.Integer(
        string="Số đêm khách sạn", readonly=True)
    nbr = fields.Integer(string="Số yêu cầu", readonly=True)

    @property
    def _table_query(self):
        return """
            SELECT
                ar.id AS id,
                ar.name AS name,
                ar.create_date AS create_date,
                ar.date_start AS date_start,
                ar.date_end AS date_end,
                ar.request_owner_id AS request_owner_id,
                he.id AS employee_id,
                hv.department_id AS department_id,
                ar.category_id AS category_id,
                ar.destination_province_id AS destination_province_id,
                ar.request_status AS request_status,
                ar.company_id AS company_id,
                ar.estimated_hotel_cost AS estimated_hotel_cost,
                ar.hotel_nights AS hotel_nights,
                1 AS nbr
            FROM approval_request ar
                JOIN approval_category ac ON ac.id = ar.category_id
                LEFT JOIN hr_employee he ON he.user_id = ar.request_owner_id
                    AND he.company_id = ar.company_id
                LEFT JOIN hr_version hv ON hv.employee_id = he.id
                    AND hv.active = True
                    AND hv.date_version = (
                        SELECT MAX(hv2.date_version)
                        FROM hr_version hv2
                        WHERE hv2.employee_id = he.id
                          AND hv2.active = True
                          AND hv2.date_version <= CURRENT_DATE
                    )
            WHERE ac.is_business_trip = 'yes'
        """
