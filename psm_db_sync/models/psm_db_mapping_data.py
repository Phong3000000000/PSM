# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.models import Constraint
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PsmDbMappingData(models.Model):
    _name = 'psm.db.mapping.data'
    _description = 'Database Mapping Data'
    _rec_name = 'complete_name'
    _order = 'mapping_model_id, model, create_date desc'

    name = fields.Char(string='Identifier', index=True, required=True,
                       help="Identifier bên ngoài cho bản ghi")
    complete_name = fields.Char(string='Tên đầy đủ', compute='_compute_complete_name',
                                store=True, index=True)

    mapping_model_id = fields.Many2one('psm.db.mapping.model', string='Ánh xạ mô hình',
                                       required=True, ondelete='cascade', index=True)
    model = fields.Char(string='Model Odoo', required=True, index=True)
    field = fields.Char(string='Field Odoo', index=True)
    res_id = fields.Integer(string='ID bản ghi', required=True, index=True)

    # Thông tin nguồn
    source_model = fields.Char(string='Model nguồn', index=True, help="Tên bảng/truy vấn ở nguồn")
    source_field = fields.Char(string='Field nguồn', index=True)
    source_id = fields.Char(string='ID nguồn', index=True)

    # Thông tin đồng bộ
    date_synced = fields.Datetime(string='Ngày đồng bộ', default=fields.Datetime.now, index=True)
    last_update_date = fields.Datetime(string='Ngày cập nhật', index=True)
    checksum = fields.Char(string='Checksum', index=True,
                           help="Checksum đánh dấu trạng thái bản ghi để xác định thay đổi")
    sync_id = fields.Many2one('psm.db.sync', string='Nhiệm vụ đồng bộ', ondelete='set null')
    log_id = fields.Many2one('psm.db.sync.log', string='Nhật ký đồng bộ', ondelete='set null')

    # Trạng thái và thống kê
    sync_count = fields.Integer(string='Số lần đồng bộ', default=1)
    company_id = fields.Many2one('res.company', string='Công ty',
                                 required=True, default=lambda self: self.env.company)

    _unique_mapping_ref = Constraint(
        'UNIQUE(mapping_model_id, model, field, source_id, source_field)',
        'Mối quan hệ ánh xạ đã tồn tại cho bản ghi này!'
    )

    @api.depends('model', 'name', 'source_id')
    def _compute_complete_name(self):
        for record in self:
            record.complete_name = f"{record.model}.{record.name} ({record.source_id})"

    def action_view_record(self):
        """Xem bản ghi đích được ánh xạ"""
        self.ensure_one()

        if not self.res_id:
            raise UserError(_('Bản ghi đích không tồn tại hoặc đã bị xóa.'))

        try:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Bản ghi đích'),
                'view_mode': 'form',
                'res_model': self.model,
                'res_id': self.res_id,
                'target': 'current',
            }
        except Exception as e:
            raise UserError(_('Không thể xem bản ghi: %s') % str(e))

    @api.model
    def create_or_update_mapping(self, mapping_model_id, model, field, res_id, source_id,
                                 source_model=False, source_field=False, checksum=False, sync_id=False, log_id=False):
        existing = self.search([
            ('mapping_model_id', '=', mapping_model_id),
            ('model', '=', model), ('field', '=', field),
            ('source_field', '=', source_field), ('source_id', '=', source_id)
        ])

        name = f"{source_field}.{source_id}_{source_field}.{model}"
        if not existing:
            existing = self.create({
                'name': name,
                'mapping_model_id': mapping_model_id,
                'model': model,
                'field': field,
                'source_id': source_id,
                'source_field': source_field,

                'res_id': res_id,
                'checksum': checksum,
                'sync_id': sync_id,
                'log_id': log_id,
                'source_model': source_model
            })
        else:
            existing.write({
                'res_id': res_id,
                'checksum': checksum,
                'sync_id': sync_id,
                'log_id': log_id,
                'source_model': source_model,

                'last_update_date': fields.Datetime.now(),
                'sync_count': existing.sync_count + 1,
            })
        return existing
