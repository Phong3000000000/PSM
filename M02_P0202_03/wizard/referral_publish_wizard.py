# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ReferralPublishWizard(models.TransientModel):
    _name = 'referral.publish.wizard'
    _description = 'Publish Referral Program Wizard'

    request_id = fields.Many2one('employee.referral.program', string='Chương trình giới thiệu', required=True)
    name = fields.Char(string='Tên bài viết', required=True)
    description = fields.Html(string='Nội dung bài viết')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id') or self.env.context.get('default_request_id') or self.env.context.get('default_program_id')
        if active_id:
            request = self.env['employee.referral.program'].browse(active_id)
            store_name = request.store_id.name if request.store_id else 'Cửa hàng'
            res['name'] = request.name or f'Chương trình giới thiệu - {store_name}'
            res['request_id'] = request.id
            config = self.env['employee.referral.config'].sudo().get_config(
                request.store_id.id if request.store_id else None
            )
            if config and config.default_post_template:
                res['description'] = Markup(config.default_post_template or '') + Markup(
                    self._build_position_table(request)
                )
            else:
                res['description'] = Markup(self._build_default_description(request))
        return res

    @api.model
    def _build_position_table(self, request):
        """Build HTML table of job positions for the post.
        Supports both flows:
          - Old flow: positions in request.request_line_ids (fields: quantity, wage, bonus_amount)
          - New flow: positions in request.line_ids (fields: positions_needed, salary, bonus_override)
        """
        # Prefer line_ids (new Approval Request flow), fallback to request_line_ids (old flow)
        lines_new = request.line_ids if hasattr(request, 'line_ids') else []
        lines_old = request.request_line_ids if hasattr(request, 'request_line_ids') else []

        if not lines_new and not lines_old:
            return ''

        rows = ''
        if lines_new:
            for line in lines_new:
                job_type_label = dict(line._fields['job_type'].selection).get(line.job_type, line.job_type) if line.job_type else ''
                wage_str = '{:,.0f} VNĐ'.format(line.salary) if line.salary else '—'
                bonus_str = '{:,.0f} VNĐ'.format(line.bonus_override or line.bonus_amount) if (line.bonus_override or line.bonus_amount) else '—'
                rows += f'''
                <tr>
                    <td style="padding:8px;border:1px solid #dee2e6;">{line.job_id.name or ''}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:center;">{job_type_label}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:center;">{line.positions_needed}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:right;">{wage_str}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:right;">{bonus_str}</td>
                </tr>'''
        else:
            for line in lines_old:
                job_type_label = dict(line._fields['job_type'].selection).get(line.job_type, line.job_type) if line.job_type else ''
                wage_str = '{:,.0f} VNĐ'.format(line.wage) if line.wage else '—'
                bonus_str = '{:,.0f} VNĐ'.format(line.bonus_amount) if line.bonus_amount else '—'
                rows += f'''
                <tr>
                    <td style="padding:8px;border:1px solid #dee2e6;">{line.job_id.name or ''}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:center;">{job_type_label}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:center;">{line.quantity}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:right;">{wage_str}</td>
                    <td style="padding:8px;border:1px solid #dee2e6;text-align:right;">{bonus_str}</td>
                </tr>'''

        return Markup(f'''
            <h3>📋 Vị trí tuyển dụng</h3>
            <table style="width:100%;border-collapse:collapse;margin:10px 0;">
                <thead>
                    <tr style="background:#875A7B;color:#fff;">
                        <th style="padding:8px;border:1px solid #dee2e6;text-align:left;">Vị trí</th>
                        <th style="padding:8px;border:1px solid #dee2e6;">Hình thức</th>
                        <th style="padding:8px;border:1px solid #dee2e6;">SL cần</th>
                        <th style="padding:8px;border:1px solid #dee2e6;">Lương</th>
                        <th style="padding:8px;border:1px solid #dee2e6;">Thưởng GT</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>''')

    @api.model
    def _build_default_description(self, request):
        store_name = request.store_id.name if request.store_id else ''
        session_name = request.recruitment_session_id.name if request.recruitment_session_id else ''
        header = f'''
            <h2>🎉 Chương trình Giới thiệu Nhân viên</h2>
            <p>Chúng tôi đang tìm kiếm nhân tài cho <strong>{store_name}</strong>
            {f"trong <em>{session_name}</em>" if session_name else ""}.</p>
            <p>Hãy giới thiệu người thân / bạn bè phù hợp để nhận thưởng hấp dẫn! 🏆</p>'''
        return Markup(header) + self._build_position_table(request)

    def action_publish(self):
        self.ensure_one()
        request = self.request_id

        # Support both old flow (request_line_ids) and new flow (line_ids from approval)
        if not request.line_ids and not request.request_line_ids:
            raise UserError(_("Yêu cầu này không có vị trí nào để đăng tuyển!"))

        # Kiểm tra cấu hình tiền thưởng
        config = self.env['employee.referral.config'].sudo().get_config(
            request.store_id.id if request.store_id else None
        )
        if not config:
            raise UserError(_(
                "Vui lòng vào Configuration → Cấu hình thưởng & Đợt → Tham số tiền thưởng để thiết lập trước khi đăng bài."
            ))

        # Update the program with wizard name/description
        request.write({
            'name': self.name,
            'description': self.description,
        })

        # Sync request_line_ids → program.line_ids if not already present
        if not request.line_ids and request.request_line_ids:
            for line in request.request_line_ids:
                self.env['employee.referral.program.line'].create({
                    'program_id': request.id,
                    'job_id': line.job_id.id,
                    'positions_needed': line.quantity,
                    'salary': line.wage,
                    'job_type': line.job_type,
                    'bonus_override': line.bonus_amount,
                })

        # Activate program
        request.action_activate()

        request.message_post(
            body=_("Đã đăng chương trình giới thiệu: %s") % self.name,
            message_type='notification'
        )

        # Đăng bài viết lên Discuss channel để hiện trên portal
        self._post_to_discuss_channel(request)

        # Đăng bài viết lên Blog (portal social feed)
        self._post_to_blog(request)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Chương trình giới thiệu',
            'res_model': 'employee.referral.program',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _post_to_discuss_channel(self, program):
        """Post recruitment announcement to a Discuss channel for portal visibility"""
        # Ưu tiên channel từ cấu hình, fallback sang General
        config = self.env['employee.referral.config'].sudo().get_config(
            program.store_id.id if program.store_id else None
        )
        channel = config.announcement_channel_id if config and config.announcement_channel_id else False
        if not channel:
            channel = self.env['discuss.channel'].sudo().search([
                ('name', 'ilike', 'general')
            ], limit=1)
        if not channel:
            return

        store_name = program.store_id.name if program.store_id else ''
        end_date = program.end_date.strftime('%d/%m/%Y') if program.end_date else 'N/A'

        referral_url = '/referral/jobs/%s' % program.id
        body = Markup(
            '<h3>🎯 %s</h3>'
            '<p>%s • HH: %s</p>'
            '%s'
            '<p>👉 <a href="%s">Xem chi tiết và giới thiệu ứng viên</a></p>'
        ) % (
            self.name,
            store_name,
            end_date,
            self.description or '',
            referral_url,
        )

        try:
            channel.sudo().message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        except (ValueError, Exception):
            # Odoo 19 có thể không hỗ trợ message_type='comment'
            channel.sudo().message_post(body=body)

    def _post_to_blog(self, program):
        """Create a blog post on the portal for the referral program"""
        config = self.env['employee.referral.config'].sudo().get_config(
            program.store_id.id if program.store_id else None
        )
        blog = config.news_blog_id if config and config.news_blog_id else False
        if not blog:
            # Tìm blog mặc định
            blog = self.env['blog.blog'].sudo().search([], limit=1)
        if not blog:
            return

        store_name = program.store_id.name if program.store_id else ''
        end_date = program.end_date.strftime('%d/%m/%Y') if program.end_date else 'N/A'

        referral_url = '/referral/jobs/%s' % program.id
        content = Markup(
            '<p>🎯 <strong>%s</strong></p>'
            '<p>📍 %s • ⏰ HH: %s</p>'
            '%s'
            '<p>👉 <a href="%s">Xem chi tiết và giới thiệu ứng viên</a></p>'
        ) % (
            self.name,
            store_name,
            end_date,
            self.description or '',
            referral_url,
        )

        try:
            self.env['blog.post'].sudo().create({
                'name': self.name,
                'blog_id': blog.id,
                'content': content,
                'is_published': True,
                'website_published': True,
            })
        except Exception:
            pass
