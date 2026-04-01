from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)

class McdAvailabilityRequest(models.Model):
    _inherit = 'mcd.availability.request'

    def action_approve(self):
        # Call super first to change state
        res = super(McdAvailabilityRequest, self).action_approve()
        
        sent_count = 0
        trainer_names = []
        
        # Send training notification logic
        for record in self:
            if record.is_trainee_shift or record.position_id.area in ['service', 'kitchen']:
                count, names = record._send_training_notification()
                sent_count += count
                trainer_names.extend(names)
        
        if sent_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Training Emails Sent!'),
                    'message': _('Đã gửi email thông báo cho %s Trainers: %s', sent_count, ', '.join(set(trainer_names))),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'}, # Close wizard/dialog if any
                }
            }
        elif self.exists() and (self[0].is_trainee_shift or self[0].position_id.area in ['service', 'kitchen']):
             # Logic ran but no emails sent (e.g. no trainers found)
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Email Sent'),
                    'message': _('Không tìm thấy Trainer nào phù hợp hoặc chưa cấu hình email!'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
            
        return res

    def _send_training_notification(self):
        """
        Returns: (int: count_sent, list: trainer_names)
        """
        self.ensure_one()
        
        # Skip if not a trainee shift and position area is not Service/Kitchen
        if not self.is_trainee_shift and self.position_id.area not in ['service', 'kitchen']:
            return 0, []
        
        # Find Trainers - employees with job title containing "Trainer"
        trainers = self.env['hr.employee'].sudo().search([
            '|',
            ('job_id.name', 'ilike', 'Crew Trainer'),
            ('job_id.name', 'ilike', 'Barista Trainer')
        ])
        
        # If not a trainee shift, filter trainers by overlapping schedule
        if not self.is_trainee_shift:
            # Check for trainers with overlapping shifts on same date
            PlanningSlot = self.env['planning.slot'].sudo()
            trainers_with_overlap = self.env['hr.employee']
            
            for trainer in trainers:
                if not trainer.resource_id:
                    continue
                # Check if trainer has a slot overlapping this request
                overlap = PlanningSlot.search([
                    ('resource_id', '=', trainer.resource_id.id),
                    ('start_datetime', '<=', self.end_datetime),
                    ('end_datetime', '>=', self.start_datetime),
                    ('state', 'in', ['draft', 'published'])
                ], limit=1)
                
                if overlap:
                    trainers_with_overlap |= trainer
            
            trainers = trainers_with_overlap
        
        if not trainers:
            _logger.info(f"No trainers found for training notification (request {self.id})")
            return 0, []
        
        # Get email templates FROM NEW MODULE M02_P0209_01
        trainer_template = self.env.ref('M02_P0209_01.mail_template_trainer_training_notification', raise_if_not_found=False)
        trainee_template = self.env.ref('M02_P0209_01.mail_template_trainee_training_notification', raise_if_not_found=False)
        
        sent_trainers = []
        
        # Send email to each trainer
        for trainer in trainers:
            trainer_email = trainer.work_email or (trainer.user_id and trainer.user_id.email)
            if not trainer_email:
                _logger.warning(f"Trainer {trainer.name} has no email configured")
                continue
            
            if trainer_template:
                try:
                    trainer_template.with_context(
                        trainer_email=trainer_email,
                        trainer_name=trainer.name
                    ).send_mail(self.id, force_send=True)
                    _logger.info(f"Training notification sent to trainer: {trainer.name} ({trainer_email})")
                    sent_trainers.append(trainer.name)
                except Exception as e:
                    _logger.exception(f"Failed to send email to trainer {trainer.name}: {e}")
        
        # Send email to trainee
        trainee_email = self.employee_id.work_email or (self.employee_id.user_id and self.employee_id.user_id.email)
        if trainee_email and trainee_template:
            try:
                # Use first trainer name if available
                first_trainer_name = trainers[0].name if trainers else 'Sẽ được thông báo sau'
                trainee_template.with_context(
                    trainer_name=first_trainer_name
                ).send_mail(self.id, force_send=True)
                _logger.info(f"Training notification sent to trainee: {self.employee_id.name} ({trainee_email})")
            except Exception as e:
                _logger.exception(f"Failed to send email to trainee {self.employee_id.name}: {e}")
                
        return len(sent_trainers), sent_trainers
