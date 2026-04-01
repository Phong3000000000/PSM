# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

def create_recruitment_stages(env):
    """Create default recruitment stages for store and office"""
    Stage = env['hr.recruitment.stage']
    
    # Store stages
    store_stages = [
        {'name': 'New', 'sequence': 10, 'recruitment_type': 'store'},
        {'name': 'Review Tiêu chí', 'sequence': 20, 'recruitment_type': 'store'},
        {'name': 'Interview', 'sequence': 30, 'recruitment_type': 'store'},
        {'name': 'OJE', 'sequence': 40, 'recruitment_type': 'store'},
        {'name': 'Thử việc', 'sequence': 50, 'recruitment_type': 'store'},
        {'name': 'Đề xuất chính thức', 'sequence': 60, 'recruitment_type': 'store'},
        {'name': 'Chính thức', 'sequence': 70, 'recruitment_type': 'store', 'hired_stage': True, 'fold': True},
    ]
    
    # Office stages
    office_stages = [
        {'name': 'New', 'sequence': 10, 'recruitment_type': 'office'},
        {'name': 'Review Tiêu chí', 'sequence': 20, 'recruitment_type': 'office'},
        {'name': 'Interview', 'sequence': 30, 'recruitment_type': 'office'},
        {'name': 'Technical Test', 'sequence': 40, 'recruitment_type': 'office'},
        {'name': 'Thử việc', 'sequence': 50, 'recruitment_type': 'office'},
        {'name': 'Đề xuất chính thức', 'sequence': 60, 'recruitment_type': 'office'},
        {'name': 'Chính thức', 'sequence': 70, 'recruitment_type': 'office', 'hired_stage': True, 'fold': True},
    ]
    
    for stage_vals in store_stages:
        existing = Stage.search([
            ('name', '=', stage_vals['name']),
            ('recruitment_type', '=', 'store')
        ], limit=1)
        if not existing:
            Stage.create(stage_vals)
            _logger.info(f"Created store stage: {stage_vals['name']}")
    
    for stage_vals in office_stages:
        existing = Stage.search([
            ('name', '=', stage_vals['name']),
            ('recruitment_type', '=', 'office')
        ], limit=1)
        if not existing:
            Stage.create(stage_vals)
            _logger.info(f"Created office stage: {stage_vals['name']}")

def create_interview_schedules(env):
    """Auto-create interview schedules for all companies"""
    InterviewSchedule = env['interview.schedule']
    Company = env['res.company']
    
    # Get all companies (except main company)
    companies = Company.search([('parent_id', '!=', False)])
    
    # Get next Monday (start of next week)
    today = datetime.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    
    for company in companies:
        # Check if schedule already exists for this company
        existing = InterviewSchedule.search([
            ('company_id', '=', company.id)
        ], limit=1)
        
        if not existing:
            # Create interview schedule with sample dates
            schedule_vals = {
                'company_id': company.id,
                'week_start_date': next_monday.date(),
                'interview_date_1': next_monday.date(),
                'interview_date_2': (next_monday + timedelta(days=2)).date(),  # Wednesday
                'interview_date_3': (next_monday + timedelta(days=4)).date(),  # Friday
                'state': 'draft',
            }
            InterviewSchedule.create(schedule_vals)
            _logger.info(f"Created interview schedule for company: {company.name}")

def post_init_hook(env):
    """Post-installation hook to create stages and schedules"""
    create_recruitment_stages(env)
    create_interview_schedules(env)
