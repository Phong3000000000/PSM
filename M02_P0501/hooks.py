# -*- coding: utf-8 -*-

from odoo import Command, fields

def post_init_hook(env):
    """Seed the 0501 demo budget for the store package project."""
    project = env.ref('M02_P0501.m02_p0501_store_package_test01', raise_if_not_found=False)
    if not project:
        return

    if not project.account_id:
        project._create_analytic_account()

    if not project.account_id:
        return

    budget = env['budget.analytic'].search([
        ('name', '=', '0501 Budget - Test01'),
        ('date_from', '=', fields.Date.to_date('2026-01-01')),
        ('date_to', '=', fields.Date.to_date('2026-12-31')),
    ], limit=1)
    if budget:
        return

    plan_fname = project.account_id.plan_id._column_name()
    budget = env['budget.analytic'].create({
        'name': '0501 Budget - Test01',
        'date_from': '2026-01-01',
        'date_to': '2026-12-31',
        'budget_type': 'expense',
        'budget_line_ids': [
            Command.create({plan_fname: project.account_id.id, 'budget_amount': 30000}),
            Command.create({plan_fname: project.account_id.id, 'budget_amount': 20000}),
            Command.create({plan_fname: project.account_id.id, 'budget_amount': 15000}),
            Command.create({plan_fname: project.account_id.id, 'budget_amount': 35000}),
        ],
    })
    budget.action_budget_confirm()
