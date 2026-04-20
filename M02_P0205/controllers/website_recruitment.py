# -*- coding: utf-8 -*-
import logging
from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment

_logger = logging.getLogger(__name__)


class WebsiteHrRecruitmentExtend(WebsiteHrRecruitment):
    """
    Override insert_record để:
    1. Inject context 'from_website=True' khi tạo hr.applicant -> model's create() tạo activity cho Recruiter
    2. Lưu job_id vào session -> template trang Congratulations đọc để hiện đúng link survey theo job
    """

    def insert_record(self, request, model_sudo, values, custom, meta=None):
        if model_sudo.model == 'hr.applicant':
            # 1. Inject from_website context khi tạo applicant
            record = request.env[model_sudo.model].with_user(SUPERUSER_ID).with_context(
                mail_create_nosubscribe=True,
                from_website=True,
            ).create(values)

            if custom or meta:
                from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
                from odoo.tools.translate import _
                _custom_label = "%s\n___________\n\n" % _("Other Information:")
                default_field = model_sudo.website_form_default_field_id
                default_field_data = values.get(default_field.name, '')
                custom_content = (default_field_data + "\n\n" if default_field_data else '') \
                    + (_custom_label + custom + "\n\n" if custom else '') \
                    + ("Metadata\n________\n\n" + meta if meta else '')

                if default_field.name:
                    record.update({default_field.name: custom_content})
                elif hasattr(record, '_message_log'):
                    record._message_log(
                        body=nl2br_enclose(custom_content, 'p'),
                        message_type='comment',
                    )

            # 2. Lưu job_id vào session để template Congratulations dùng
            if record.job_id:
                request.session['mcd_last_applicant_job_id'] = record.job_id.id
                _logger.info(
                    "MCD: Saved job_id=%s (survey_id=%s) to session for thank-you page",
                    record.job_id.id,
                    record.job_id.survey_id.id if record.job_id.survey_id else None,
                )
            else:
                request.session.pop('mcd_last_applicant_job_id', None)

            return record.id

        # For other models, use default behavior
        return super().insert_record(request, model_sudo, values, custom, meta)
