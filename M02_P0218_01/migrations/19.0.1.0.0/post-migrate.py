# -*- coding: utf-8 -*-
# Run this in Odoo shell or as a one-time migration script
# This will delete the old template and let the XML recreate it

def migrate(cr, version):
    """Delete old email template to force recreation with correct syntax"""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Find and delete old template
    old_template = env.ref('M02_P0218_01.email_template_salary_increase_approved', raise_if_not_found=False)
    if old_template:
        old_template.unlink()
        print("✅ Deleted old email template - will be recreated on module load")
