from odoo import fields, models

class ApprovalAirline(models.Model):
    _name = "approval.airline"
    _description = "Airline"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)

class ApprovalTicketClass(models.Model):
    _name = "approval.ticket.class"
    _description = "Ticket Class"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)
