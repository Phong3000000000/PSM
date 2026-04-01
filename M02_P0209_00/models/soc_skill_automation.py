from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SlideSlidePartner(models.Model):
    _inherit = 'slide.slide.partner'

    def _grant_soc_skill(self):
        """
        B11: Update Profile - Auto-grant skill upon SOC completion.
        Triggered when 'completed' becomes True.
        """
        for record in self:
            if not record.completed or not record.slide_id.is_soc:
                continue
            
            skill = record.slide_id.soc_skill_id
            level = record.slide_id.soc_skill_level_id
            user = record.partner_id.user_ids[:1] # Get user from partner
            if not user:
                continue
                
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            
            if employee and skill and level:
                # Check if employee already has this skill
                existing_skill = self.env['hr.employee.skill'].search([
                    ('employee_id', '=', employee.id),
                    ('skill_id', '=', skill.id)
                ], limit=1)

                if existing_skill:
                    # Upgrade level: Check if new level is higher
                    # Assuming level.level_progress maps to numeric value (0-100)
                    if level.level_progress > existing_skill.skill_level_id.level_progress:
                        existing_skill.write({'skill_level_id': level.id})
                        # Log/Notify
                        record.slide_id.message_post(body=f"Skill Upgraded for {employee.name}: {skill.name} -> {level.name}")
                else:
                    # Create new skill
                    self.env['hr.employee.skill'].create({
                        'employee_id': employee.id,
                        'skill_id': skill.id,
                        'skill_level_id': level.id,
                        'skill_type_id': skill.skill_type_id.id,
                    })
                    # Log/Notify
                    record.slide_id.message_post(body=f"Skill Granted to {employee.name}: {skill.name} - {level.name}")


    @api.model_create_multi
    def create(self, vals_list):
        records = super(SlideSlidePartner, self).create(vals_list)
        for record in records:
            if record.completed:
                record._grant_soc_skill()
        return records

    def write(self, vals):
        res = super(SlideSlidePartner, self).write(vals)
        if 'completed' in vals and vals['completed']:
            self._grant_soc_skill()
        return res
