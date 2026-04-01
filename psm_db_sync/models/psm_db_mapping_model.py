# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.models import Constraint
from odoo.exceptions import UserError, ValidationError
import json

_logger = logging.getLogger(__name__)


class PsmDbMappingModel(models.Model):
    _name = 'psm.db.mapping.model'
    _description = 'Database Mapping Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'connection_id, target_model_id'

    name = fields.Char(string='Tên ánh xạ', required=True, tracking=True, index=True)
    connection_id = fields.Many2one('psm.db.connection', string='Kết nối CSDL',
                                    required=True, tracking=True, ondelete='cascade')
    source_type = fields.Selection([
        ('table', 'Bảng'),
        ('query', 'Truy vấn SQL')
    ], string='Kiểu nguồn dữ liệu', required=True, default='table', tracking=True)
    source_table = fields.Char(string='Bảng nguồn', tracking=True)
    source_query = fields.Text(string='Truy vấn SQL', tracking=True)
    source_query_with_recursive = fields.Text(string='Truy vấn SQL với đệ quy',
                                              tracking=True,
                                              help="Truy vấn SQL có thể sử dụng đệ quy nếu cần thiết")

    target_model_id = fields.Many2one('ir.model', string='Model đích',
                                      required=True, tracking=True, ondelete='cascade')
    target_model = fields.Char(related='target_model_id.model', string='Tên Model đích', readonly=True)

    # Key configuration
    source_key_field = fields.Char(string='Trường khóa nguồn', required=True, tracking=True,
                                   help="Trường dùng để xác định bản ghi (thường là ID)")
    target_key_field = fields.Char(string='Trường khóa đích', required=True, tracking=True,
                                   help="Trường dùng để xác định bản ghi đích")

    # Performance options
    batch_size = fields.Integer(string='Kích thước lô', default=50, tracking=True,
                                help="Số bản ghi xử lý trong mỗi lô")
    use_checksum = fields.Boolean(string='Dùng checksum', default=False, tracking=True,
                                  help="Dùng checksum để kiểm tra thay đổi thay vì so sánh từng trường")
    config_ok = fields.Boolean(string='Hoàn tất cấu hình', compute='_compute_config_ok')

    # Last sync info
    last_sync_date = fields.Datetime(string='Đồng bộ gần nhất',
                                     compute='_compute_last_sync_info', store=True)
    last_record_count = fields.Integer(string='Số bản ghi gần nhất',
                                       compute='_compute_last_sync_info', store=True)

    # Relations
    field_mapping_ids = fields.One2many('psm.db.mapping.field', 'mapping_model_id', string='Ánh xạ trường')
    field_mapping_count = fields.Integer(compute='_compute_field_mapping_count', string='Số lượng trường')
    sync_config_ids = fields.One2many('psm.db.sync', 'mapping_model_id', string='Cấu hình đồng bộ')
    sync_log_ids = fields.One2many('psm.db.sync.log', 'mapping_model_id', string='Nhật ký đồng bộ')

    # System fields
    active = fields.Boolean(string='Đang hoạt động', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Công ty',
                                 required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Người phụ trách',
                              default=lambda self: self.env.user, tracking=True)

    _unique_source_target = Constraint(
        'UNIQUE(connection_id, source_table, target_model_id)',
        'Ánh xạ cho nguồn và đích này đã tồn tại!'
    )

    @api.depends('sync_config_ids.last_sync_date', 'sync_config_ids.last_log_id')
    def _compute_last_sync_info(self):
        """Tự động tính toán thông tin sync gần nhất"""
        for record in self:
            # Tìm sync config gần nhất có log
            latest_sync = record.sync_config_ids.filtered(lambda r: r.last_log_id and r.last_sync_date).sorted(
                'last_sync_date', reverse=True)[:1]
            # latest_sync = record.sync_config_ids.filtered('last_log_id').sorted('last_sync_date', reverse=True)[:1]

            if latest_sync and latest_sync.last_log_id:
                record.last_sync_date = latest_sync.last_sync_date
                record.last_record_count = (
                        latest_sync.last_log_id.records_created +
                        latest_sync.last_log_id.records_updated
                )
            else:
                record.last_sync_date = False
                record.last_record_count = 0

    @api.depends('field_mapping_ids')
    def _compute_config_ok(self):
        for record in self:
            record.config_ok = record.field_mapping_ids != False

    def action_check_mapping_ready_for_sync(self):
        """Kiểm tra mapping có sẵn sàng sync không"""
        self.ensure_one()
        errors = []

        # 1. Kiểm tra có field mappings không
        if not self.field_mapping_ids:
            errors.append("Chưa có field mapping nào")
            return errors

        # 2. Kiểm tra key field
        key_mapping = self.field_mapping_ids.filtered('is_key_field')
        if not key_mapping:
            errors.append(f"Chưa có mapping cho key field '{self.source_key_field}'")

        # 3. Kiểm tra relation mappings
        relation_fields = self.field_mapping_ids.filtered(
            lambda m: m.transformation_type == 'relation'
        )
        for rel_field in relation_fields:
            if not rel_field.relation_model_id:
                errors.append(f"Field '{rel_field.source_field}' chưa có relation mapping")

        return errors

    @api.onchange('source_type', 'source_table', 'target_model_id')
    def _onchange_clear_field_mappings(self):
        self.field_mapping_ids = False

    @api.depends('field_mapping_ids')
    def _compute_field_mapping_count(self):
        for record in self:
            record.field_mapping_count = len(record.field_mapping_ids)

    @api.onchange('source_type')
    def _onchange_source_type(self):
        if self.source_type == 'table':
            self.source_query = False
            self.source_query_with_recursive = False
        else:
            self.source_table = False

    @api.onchange('target_model_id')
    def _onchange_target_model_id(self):
        if self.target_model_id:
            self.target_key_field = 'id'

    @api.constrains('source_type', 'source_table', 'source_query')
    def _check_source_config(self):
        for record in self:
            if record.source_type == 'table' and not record.source_table:
                raise ValidationError(_('Vui lòng chọn bảng nguồn!'))
            if record.source_type == 'query' and not record.source_query:
                raise ValidationError(_('Vui lòng nhập truy vấn SQL!'))

    def action_view_field_mappings(self):
        self.ensure_one()
        return {
            'name': _('Ánh xạ trường'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.mapping.field',
            'view_mode': 'tree,form',
            'domain': [('mapping_model_id', '=', self.id)],
            'context': {'default_mapping_model_id': self.id},
        }

    def action_view_sync_history(self):
        self.ensure_one()
        return {
            'name': _('Lịch sử đồng bộ'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.sync.log',
            'view_mode': 'tree,form',
            'domain': [('mapping_model_id', '=', self.id)],
            'context': {'default_mapping_model_id': self.id},
        }

    def _check_exists_target_key_field(self):
        field_info = self.env[self.target_model]._fields.get(self.target_key_field)
        if not field_info:
            raise UserError(
                _('Trường khóa đích "%s" không tồn tại trong model "%s"') % (self.target_key_field, self.target_model))

    def action_get_source_fields(self):
        self.ensure_one()
        self._check_exists_target_key_field()

        if not self.connection_id:
            raise UserError(_('Vui lòng chọn kết nối trước!'))

        try:
            fields_data = []
            if self.source_type == 'table':
                if not self.source_table:
                    raise UserError(_('Vui lòng chọn bảng nguồn!'))

                columns = self.connection_id.get_table_columns(self.source_table)
                for column in columns:
                    fields_data.append({
                        'name': column['name'],
                        'data_type': str(column['type']),
                        'nullable': column.get('nullable', True),
                    })
            else:
                if not self.source_query:
                    raise UserError(_('Vui lòng nhập truy vấn SQL!'))

                engine = self.connection_id.db_type
                source_query = self.source_query.strip().rstrip(';')

                if engine in ['postgresql', 'mysql', 'mariadb']:
                    test_query = f"SELECT * FROM ({source_query}) AS query_result LIMIT 1"
                elif engine == 'oracle':
                    test_query = f"SELECT * FROM ({source_query}) query_result WHERE ROWNUM <= 1"
                elif engine == 'mssql':
                    test_query = f"SELECT TOP 1 * FROM ({source_query}) AS query_result"
                else:
                    raise UserError(_("Không hỗ trợ kiểu cơ sở dữ liệu này"))

                if self.source_query_with_recursive:
                    test_query = f"{self.source_query_with_recursive.strip().rstrip(';')} {test_query}"

                result = self.connection_id.execute_query(test_query)

                if not result:
                    raise UserError(_('Truy vấn không trả về dữ liệu. Vui lòng kiểm tra lại!'))

                sample_row = result[0]
                for key, value in sample_row.items():
                    inferred_type = 'UNKNOWN'
                    if isinstance(value, int):
                        inferred_type = 'INTEGER'
                    elif isinstance(value, float):
                        inferred_type = 'FLOAT'
                    elif isinstance(value, bool):
                        inferred_type = 'BOOLEAN'
                    elif isinstance(value, str):
                        inferred_type = 'TEXT'
                    elif hasattr(value, 'isoformat'):
                        inferred_type = 'DATETIME'

                    fields_data.append({
                        'name': key,
                        'data_type': inferred_type,
                        'nullable': True,
                    })

            for field_data in fields_data:
                source_field_name = field_data['name']
                target_field_name = None

                # Kiểm tra xem trường này đã được ánh xạ chưa
                existing_mapping = self.field_mapping_ids.filtered(
                    lambda m: m.source_field == source_field_name
                )

                if existing_mapping:
                    if not existing_mapping.target_field_type:
                        existing_mapping._compute_target_field_info()
                    continue

                # Xác định kiểu dữ liệu
                source_data_type = field_data['data_type']

                # Tạo ánh xạ trường mới
                mapping_vals = {
                    'mapping_model_id': self.id,
                    'source_field': source_field_name,
                    'source_field_type': source_data_type,
                }

                field_mapping_id = self.env['psm.db.mapping.field'].create(mapping_vals)
                field_mapping_id._suggest_transformation_type()
                field_mapping_id._onchange_transformation_type()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': 'Ánh xạ trường dữ liệu đã được cập nhật',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except Exception as e:
            raise UserError(_('Lỗi khi lấy thông tin trường: %s') % str(e))

    def action_sync_now(self):
        """Tạo wizard đồng bộ thủ công"""
        self.ensure_one()
        self._check_exists_target_key_field()

        return {
            'name': _('Đồng bộ thủ công'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_mapping_model_id': self.id}
        }
