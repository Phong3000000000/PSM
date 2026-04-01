# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.models import Constraint
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

DATATYPE_MAPPING = {
    # MySQL/MariaDB types
    'INT': 'integer',
    'TINYINT': 'boolean',
    'SMALLINT': 'integer',
    'MEDIUMINT': 'integer',
    'BIGINT': 'integer',
    'FLOAT': 'float',
    'DOUBLE': 'float',
    'DECIMAL': 'float',
    'CHAR': 'char',
    'VARCHAR': 'char',
    'TEXT': 'text',
    'TINYTEXT': 'text',
    'MEDIUMTEXT': 'text',
    'LONGTEXT': 'text',
    'DATE': 'date',
    'DATETIME': 'datetime',
    'TIMESTAMP': 'datetime',
    'TIME': 'char',
    'YEAR': 'integer',
    'ENUM': 'selection',
    'SET': 'many2many',
    'BLOB': 'binary',
    'TINYBLOB': 'binary',
    'MEDIUMBLOB': 'binary',
    'LONGBLOB': 'binary',
    'JSON': 'json',

    # PostgreSQL types
    'integer': 'integer',
    'smallint': 'integer',
    'bigint': 'integer',
    'real': 'float',
    'double precision': 'float',
    'numeric': 'float',
    'text': 'text',
    'character varying': 'char',
    'character': 'char',
    'date': 'date',
    'timestamp': 'datetime',
    'timestamp with time zone': 'datetime',
    'time': 'char',
    'boolean': 'boolean',
    'bytea': 'binary',
    'json': 'json',
    'jsonb': 'json',
    'uuid': 'char',
    'interval': 'char',
    'hstore': 'text',
    'inet': 'char',
    'cidr': 'char',
    'macaddr': 'char',

    # MSSQL types
    'bit': 'boolean',
    'tinyint': 'integer',
    'smallint': 'integer',
    'int': 'integer',
    'bigint': 'integer',
    'decimal': 'float',
    'numeric': 'float',
    'float': 'float',
    'real': 'float',
    'money': 'float',
    'smallmoney': 'float',
    'char': 'char',
    'varchar': 'char',
    'text': 'text',
    'nchar': 'char',
    'nvarchar': 'char',
    'ntext': 'text',
    'binary': 'binary',
    'varbinary': 'binary',
    'image': 'binary',
    'date': 'date',
    'datetime': 'datetime',
    'datetime2': 'datetime',
    'datetimeoffset': 'datetime',
    'smalldatetime': 'datetime',
    'time': 'char',
    'uniqueidentifier': 'char',
    'xml': 'text',

    # Oracle types
    'NUMBER': 'float',
    'FLOAT': 'float',
    'DEC': 'float',
    'DECIMAL': 'float',
    'INTEGER': 'integer',
    'INT': 'integer',
    'SMALLINT': 'integer',
    'REAL': 'float',
    'DOUBLE PRECISION': 'float',
    'VARCHAR2': 'char',
    'NVARCHAR2': 'char',
    'CHAR': 'char',
    'NCHAR': 'char',
    'CLOB': 'text',
    'NCLOB': 'text',
    'LONG': 'text',
    'DATE': 'datetime',
    'TIMESTAMP': 'datetime',
    'TIMESTAMP WITH TIME ZONE': 'datetime',
    'TIMESTAMP WITH LOCAL TIME ZONE': 'datetime',
    'INTERVAL YEAR TO MONTH': 'char',
    'INTERVAL DAY TO SECOND': 'char',
    'BLOB': 'binary',
    'BFILE': 'binary',
    'RAW': 'binary',
    'LONG RAW': 'binary',
    'ROWID': 'char',
    'UROWID': 'char',
}


class PsmDbMappingField(models.Model):
    _name = 'psm.db.mapping.field'
    _description = 'Database Field Mapping'
    _order = 'target_field, sequence, id'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    mapping_model_id = fields.Many2one('psm.db.mapping.model', string='Ánh xạ mô hình',
                                       required=True, ondelete='cascade')

    # Source field details
    source_field = fields.Char(string='Trường nguồn', required=True, index=True)
    source_field_type = fields.Char(string='Kiểu dữ liệu nguồn')

    # Target field details
    target_field = fields.Char(string='Tên trường đích', compute='_compute_target_field', store=True, readonly=False)
    target_field_id = fields.Many2one('ir.model.fields', string='Trường đích', compute='_compute_target_field_info',
                                      store=True, readonly=False)
    target_field_type = fields.Char(string='Kiểu dữ liệu đích', compute='_compute_target_field_info', store=True)

    # Settings
    sequence = fields.Integer(string='Thứ tự', default=10, help="Thứ tự xử lý ánh xạ trường")
    active = fields.Boolean(string='Đang hoạt động', default=True)
    include_in_sync = fields.Boolean(string='Đồng bộ', default=True,
                                     help="Bao gồm trường này trong quá trình đồng bộ")

    is_key_field = fields.Boolean(string='Là trường khóa', compute='_compute_is_key_field', store=True)
    is_required = fields.Boolean(string='Bắt buộc', default=False)

    # Data transformation
    transformation_type = fields.Selection([
        ('direct', 'Trực tiếp'),
        ('date_format', 'Định dạng ngày'),
        ('number_format', 'Định dạng số'),
        ('mapping', 'Ánh xạ giá trị'),
        ('function', 'Hàm Python'),
        ('relation', 'Quan hệ'),
        ('static', 'Giá trị tĩnh'),
    ], string='Kiểu chuyển đổi', default='direct', required=True)

    # Date transformation
    source_date_format = fields.Char(string='Định dạng ngày nguồn',
                                     help="Ví dụ: %Y-%m-%d %H:%M:%S")
    target_date_format = fields.Char(string='Định dạng ngày đích',
                                     help="Ví dụ: %Y-%m-%d %H:%M:%S")

    # Number transformation
    decimal_separator = fields.Char(string='Dấu phân cách thập phân', default='.')
    thousands_separator = fields.Char(string='Dấu phân cách hàng nghìn', default=',')
    round_precision = fields.Integer(string='Làm tròn', default=2)

    # Value mapping
    value_mapping = fields.Text(string='Ánh xạ giá trị',
                                help="JSON định dạng {'giá_trị_nguồn': 'giá_trị_đích'}")

    # Function transformation
    python_function = fields.Text(string='Hàm Python',
                                  help="Định nghĩa hàm Python để xử lý dữ liệu")

    # Relation mapping
    relation_model_id = fields.Many2one('psm.db.mapping.model', string='Ánh xạ quan hệ')
    relation_field = fields.Char(string='Trường quan hệ', related='relation_model_id.target_key_field')
    relation_create_auto = fields.Boolean(string='Tự động đồng bộ relation',
        default=False, help="Tự động đồng bộ bản ghi relation từ source nếu chưa có")

    # Static value
    static_value = fields.Char(string='Giá trị tĩnh')

    # Advanced settings
    default_value = fields.Char(string='Giá trị mặc định',
                                help="Giá trị mặc định khi dữ liệu nguồn trống")

    skip_if_empty = fields.Boolean(string='Bỏ qua nếu trống', default=False)
    validation_regex = fields.Char(string='Regex xác thực')
    convert_empty_to_false = fields.Boolean(string='Chuyển trống thành False', default=True)
    trim_whitespace = fields.Boolean(string='Cắt khoảng trắng', default=True)
    force_uppercase = fields.Boolean(string='Chuyển chữ hoa', default=False)
    force_lowercase = fields.Boolean(string='Chuyển chữ thường', default=False)

    _unique_mapping_source_field = Constraint(
        'UNIQUE(mapping_model_id, source_field)',
        'Trường nguồn đã được ánh xạ!'
    )

    @api.depends('source_field', 'mapping_model_id.source_key_field')
    def _compute_is_key_field(self):
        for record in self:
            record.is_key_field = record.source_field == record.mapping_model_id.source_key_field

    @api.constrains('is_required')
    def _check_is_key_field(self):
        for record in self.filtered(lambda x: x.is_key_field and not x.is_required):
            record.is_required = True

    @api.depends('source_field', 'target_field')
    def _compute_name(self):
        for record in self:
            if record.source_field and record.target_field:
                record.name = f"{record.source_field} → {record.target_field}"
            elif record.source_field:
                record.name = record.source_field
            else:
                record.name = _("Ánh xạ trường mới")

    @api.depends('source_field')
    def _compute_target_field(self):
        for record in self:
            model_fields = self.env['ir.model.fields'].search([
                ('model_id', '=', record.mapping_model_id.target_model_id.id)
            ])
            model_fields_dict = {field.name: field for field in model_fields}
            target_field = False
            if record.source_field in model_fields_dict:
                target_field = model_fields_dict[record.source_field].name
            else:
                # Tìm field có tên tương tự
                for odoo_field_name, odoo_field in model_fields_dict.items():
                    if record.source_field.lower().replace('_', '') == odoo_field_name.lower().replace('_', ''):
                        target_field = odoo_field.name
            record.target_field = target_field

    @api.depends('target_field', 'mapping_model_id.target_model_id')
    def _compute_target_field_info(self):
        for record in self:
            target_field_id = False
            is_required = False
            field_default = False
            field_type = False

            if record.target_field and record.mapping_model_id and record.mapping_model_id.target_model_id:
                model_name = record.mapping_model_id.target_model_id.model

                try:
                    if model_name in self.env:
                        # Lấy field definition từ Python object
                        field_info = self.env[model_name]._fields.get(record.target_field)
                        if field_info:
                            is_required = getattr(field_info, 'required', False)
                            field_default = getattr(field_info, 'default', False)
                            field_type = getattr(field_info, 'type', False)

                            # Tìm ir.model.fields record tương ứng
                            target_field_record = record.mapping_model_id.target_model_id.field_id.filtered(
                                lambda x: x.name == record.target_field
                            )[:1]

                            if target_field_record:
                                target_field_id = target_field_record.id
                    else:
                        _logger.warning(f"Mô hình {model_name} không tìm thấy trong hệ thống")

                except Exception as e:
                    _logger.error(f"Lỗi tính toán thông tin trường đích cho {model_name}.{record.target_field}: {str(e)}")

            record.target_field_id = target_field_id
            record.is_required = is_required
            record.target_field_type = field_type

    @api.onchange('source_field', 'source_field_type', 'target_field', 'target_field_type')
    def _suggest_transformation_type(self):
        """Đề xuất transformation type dựa theo dữ liệu lịch sử"""
        if self.target_field_type:
            domain = [
                ('target_field', '=', self.target_field),
                ('target_field_type', '=', self.target_field_type),
                ('transformation_type', '!=', 'direct'),
            ]

            # Chỉ exclude ID nếu là integer
            if self.id and isinstance(self.id, int):
                domain.append(('id', '!=', self.id))

            similar_mapping = self.env['psm.db.mapping.field'].search(domain, limit=1, order='id desc')

            if similar_mapping:
                self.transformation_type = similar_mapping.transformation_type

        if self.transformation_type in (False, 'direct'):
            for db_type, odoo_type in DATATYPE_MAPPING.items():
                if db_type.upper() in self.source_field_type.upper():
                    if odoo_type in ('date', 'datetime'):
                        self.transformation_type = 'date_format'
                        self.source_date_format = '%Y-%m-%d' if odoo_type == 'date' else '%Y-%m-%d %H:%M:%S'
                        self.target_date_format = '%Y-%m-%d' if odoo_type == 'date' else '%Y-%m-%d %H:%M:%S'
                    elif odoo_type in ('float', 'monetary'):
                        self.transformation_type = 'number_format'
                    elif odoo_type == 'selection':
                        self.transformation_type = 'mapping'
                    break

    @api.onchange('transformation_type')
    def _onchange_transformation_type(self):
        """Đề xuất giá trị cấu hình mặc định dựa theo dữ liệu lịch sử"""
        if self.target_field_type == 'relation':
            domain = [
                ('target_field_id.model', '=', self.target_field_id.model or False),
                ('target_field_id.type', '=', self.target_field_id.type or False),
                ('transformation_type', '=', self.transformation_type or False),
            ]

            # Chỉ exclude ID nếu là integer
            if self.id and isinstance(self.id, int):
                domain.append(('id', '!=', self.id))

            similar_mapping = self.env['psm.db.mapping.field'].search(domain, limit=1, order='id desc')

            if similar_mapping:
                self.relation_model_id = similar_mapping.relation_model_id
                # self.relation_field = similar_mapping.relation_field
        else:
            domain = [
                ('target_field', '=', self.target_field),
                ('target_field_type', '=', self.target_field_type),
                ('transformation_type', '=', self.transformation_type),
            ]

            # Chỉ exclude ID nếu là integer
            if self.id and isinstance(self.id, int):
                domain.append(('id', '!=', self.id))

            similar_mapping = self.env['psm.db.mapping.field'].search(domain, limit=1, order='id desc')

            if similar_mapping:
                if self.transformation_type == 'date_format':
                    self.source_date_format = similar_mapping.source_date_format
                    self.target_date_format = similar_mapping.target_date_format

                elif self.transformation_type == 'number_format':
                    self.decimal_separator = similar_mapping.decimal_separator
                    self.thousands_separator = similar_mapping.thousands_separator
                    self.round_precision = similar_mapping.round_precision

                elif self.transformation_type == 'mapping':
                    self.value_mapping = similar_mapping.value_mapping

                elif self.transformation_type == 'function':
                    self.python_function = similar_mapping.python_function

                elif self.transformation_type == 'static':
                    self.static_value = similar_mapping.static_value

        if similar_mapping:
            # Copy advanced options
            self.default_value = similar_mapping.default_value
            self.skip_if_empty = similar_mapping.skip_if_empty
            self.trim_whitespace = similar_mapping.trim_whitespace
            self.force_uppercase = similar_mapping.force_uppercase
            self.force_lowercase = similar_mapping.force_lowercase

        """Reset các trường không liên quan khi đổi kiểu chuyển đổi"""
        if self.transformation_type != 'date_format':
            self.source_date_format = False
            self.target_date_format = False

        if self.transformation_type != 'number_format':
            self.decimal_separator = '.'
            self.thousands_separator = ','
            self.round_precision = 2

        if self.transformation_type != 'mapping':
            self.value_mapping = False

        if self.transformation_type != 'function':
            self.python_function = False

        if self.transformation_type != 'relation':
            self.relation_model_id = False
            # self.relation_field = False

        if self.transformation_type != 'static':
            self.static_value = False

    # @api.onchange('relation_model_id')
    # def _onchange_relation_model_id(self):
    #     if self.relation_model_id:
    #         similar_mappings = self.mapping_model_id.field_mapping_ids.filtered(
    #             lambda x: x.relation_model_id and x.relation_field
    #                       and x.relation_model_id == self.relation_model_id)[:1]
    #         if not similar_mappings:
    #             # Tìm mapping tương tự gần nhất nếu không có mapping hiện tại
    #             similar_mappings = self.env['psm.db.mapping.field'].search([
    #                 ('relation_model_id', '!=', False), ('relation_field', '!=', False),
    #                 ('relation_model_id', '=', self.relation_model_id.id)
    #
    #             ], limit=1, order='id desc')
    #
    #         if similar_mappings:
    #             self.relation_field = similar_mappings.relation_field

    def action_test_transformation(self):
        """Mở wizard để kiểm tra chuyển đổi"""
        self.ensure_one()

        return {
            'name': _('Kiểm tra chuyển đổi'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.test.transformation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_field_mapping_id': self.id}
        }

    def action_generate_python_function(self):
        """Tạo mẫu hàm Python dựa trên kiểu dữ liệu"""
        self.ensure_one()

        if self.transformation_type != 'function':
            self.transformation_type = 'function'

        template = """def transform_value(value, source_record=None, target_record=None):
    """

        if self.source_field_type and 'INT' in self.source_field_type.upper():
            template += """# Convert to integer
    try:
        if value is None or value == '':
            return 0
        return int(value)
    except (ValueError, TypeError):
        return 0"""

        elif self.source_field_type and any(
                t in self.source_field_type.upper() for t in ['FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC']):
            template += """# Convert to float
    try:
        if value is None or value == '':
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0"""

        elif self.source_field_type and any(t in self.source_field_type.upper() for t in ['DATE', 'TIME']):
            template += """# Format date/time
    from datetime import datetime
    try:
        if not value:
            return False
        if isinstance(value, str):
            # Modify the format string to match your source format
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%Y-%m-%d')
        elif isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        return False
    except Exception as e:
        return False"""

        else:
            template += """# Default transformation
    if value is None:
        return False
    return str(value)"""

        self.python_function = template

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mẫu hàm đã được tạo'),
                'message': _('Đã tạo mẫu hàm Python dựa trên kiểu dữ liệu. Vui lòng chỉnh sửa nếu cần.'),
                'sticky': False,
                'type': 'success'
            }
        }
