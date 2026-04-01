from odoo import models, fields, api


class HrEmployeeChangeHistory(models.Model):
    _name = 'hr.employee.change.history'
    _description = 'Employee Change History'
    _order = 'change_date desc'
    _rec_name = 'field_label'

    # Thông tin cơ bản
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True
    )
    approval_request_id = fields.Many2one(
        'approval.request',
        string='Approval Request',
        ondelete='set null',
        index=True
    )
    change_date = fields.Datetime(
        string='Change Date',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    changed_by_id = fields.Many2one(
        'res.users',
        string='Changed By',
        default=lambda self: self.env.user,
        ondelete='set null',
        help='User who approved the change'
    )

    # Thông tin thay đổi
    field_name = fields.Char(
        string='Field Name',
        required=True,
        help='Technical field name'
    )
    field_label = fields.Char(
        string='Field Label',
        required=True,
        help='Display label for the field'
    )
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    change_type = fields.Selection(
        [
            ('create', 'Create'),
            ('update', 'Update'),
            ('delete', 'Delete')
        ],
        string='Change Type',
        default='update',
        required=True
    )

    # Metadata
    notes = fields.Text(string='Notes')
