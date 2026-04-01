from odoo import models, fields, api

class Job(models.Model):
    _inherit = 'hr.job'

    # B5: What training is required for this job?
    # Linking to Courses (Channels) which contain the SOCs.
    course_ids = fields.Many2many(
        'slide.channel', 
        'job_course_rel', # Explicit Relation Name
        'job_id', 'channel_id',
        string='Required Training Paths',
        help='The eLearning Courses/Paths that an employee in this position must complete.'
    )

    # B17: Manager Training Logic
    manager_course_ids = fields.Many2many(
        'slide.channel',
        'job_manager_course_rel', # Explicit Relation Name
        'job_id', 'channel_id',
        string='Manager Training Paths',
        help='Training paths activated only when Employee becomes a Manager Trainee.'
    )
