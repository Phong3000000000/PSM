# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


def create_interview_schedules(env):
    """Auto-create interview schedules for all companies"""
    InterviewSchedule = env['interview.schedule']
    Company = env['res.company']
    
    companies = Company.search([('parent_id', '!=', False)])
    
    today = datetime.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    
    for company in companies:
        existing = InterviewSchedule.search([
            ('company_id', '=', company.id)
        ], limit=1)
        
        if not existing:
            schedule_vals = {
                'company_id': company.id,
                'week_start_date': next_monday.date(),
                'interview_date_1': next_monday.date(),
                'interview_date_2': (next_monday + timedelta(days=2)).date(),
                'interview_date_3': (next_monday + timedelta(days=4)).date(),
                'state': 'draft',
            }
            InterviewSchedule.create(schedule_vals)
            _logger.info(f"Created interview schedule for company: {company.name}")


def recompute_recruitment_fields(env):
    """Force recompute recruitment_type and position_level for all existing hr.job records"""
    jobs = env['hr.job'].search([])
    if jobs:
        jobs._compute_recruitment_logic()
        _logger.info(f"Recomputed recruitment fields for {len(jobs)} job positions")


def post_init_hook(env):
    """Post-installation hook"""
    create_interview_schedules(env)
    recompute_recruitment_fields(env)
    # Cleanup chạy qua cleanup_actions.xml (<function>) để chạy cả khi upgrade
