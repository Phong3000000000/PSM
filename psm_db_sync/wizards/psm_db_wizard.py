# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PsmDbWizard(models.TransientModel):
    _name = 'psm.db.wizard'
    _description = 'Database Synchronization Wizard'

    mapping_model_id = fields.Many2one('psm.db.mapping.model', string='Ánh xạ mô hình',
                                       required=True)
    sync_type = fields.Selection([
        ('full', 'Đầy đủ'),
        ('incremental', 'Tăng dần'),
        ('modified', 'Chỉ thay đổi'),
    ], string='Kiểu đồng bộ', default='full', required=True)

    sync_action = fields.Selection([
        ('create_update', 'Tạo và cập nhật'),
        ('create_only', 'Chỉ tạo mới'),
        ('update_only', 'Chỉ cập nhật'),
    ], string='Hành động', default='create_update', required=True)

    filter_where_clause = fields.Text(string='Điều kiện SQL',
                                      help="Mệnh đề WHERE SQL áp dụng với bảng/truy vấn nguồn (không cần WHERE)")

    batch_size = fields.Integer(string='Kích thước lô', default=50, required=True)
    use_queue = fields.Boolean(string='Sử dụng hàng đợi', default=True,
                               help="Sử dụng cơ chế hàng đợi (queue_job) để xử lý đồng bộ trong background")

    incremental_field = fields.Char(string='Trường tăng dần',
                                    help="Trường dùng cho đồng bộ tăng dần (vd: last_update, modified_date)")
    last_sync_value = fields.Char(string='Giá trị cuối', help="Giá trị của trường tăng dần ở lần đồng bộ gần nhất")

    state = fields.Selection([
        ('config', 'Cấu hình'),
        ('result', 'Kết quả')
    ], default='config')

    # Kết quả
    sync_log_id = fields.Many2one('psm.db.sync.log', string='Nhật ký')
    result_message = fields.Text(string='Kết quả')
    records_created = fields.Integer(string='Bản ghi tạo mới', readonly=True)
    records_updated = fields.Integer(string='Bản ghi cập nhật', readonly=True)
    records_failed = fields.Integer(string='Bản ghi lỗi', readonly=True)

    @api.onchange('mapping_model_id')
    def _onchange_mapping_model(self):
        """Đặt giá trị mặc định từ model ánh xạ"""
        if self.mapping_model_id:
            sync_configs = self.env['psm.db.sync'].search([
                ('mapping_model_id', '=', self.mapping_model_id.id),
                ('active', '=', True)
            ])
            if sync_configs.filtered(lambda x: x.execution_type == 'scheduled'):
                sync_configs = sync_configs.filtered(lambda x: x.execution_type == 'scheduled')

            if sync_configs:
                sync_configs = sync_configs[:1]
                self.sync_type = sync_configs.sync_type
                self.sync_action = sync_configs.sync_action
                self.filter_where_clause = sync_configs.filter_where_clause
                self.batch_size = sync_configs.batch_size
                self.incremental_field = sync_configs.incremental_field
                self.last_sync_value = sync_configs.last_sync_value
                self.use_queue = sync_configs.use_queue

    def action_sync(self):
        """Thực hiện đồng bộ"""
        self.ensure_one()

        if not self.mapping_model_id or not self.mapping_model_id.connection_id:
            raise UserError(_('Vui lòng chọn ánh xạ mô hình hợp lệ.'))

        # Tạo hoặc lấy cấu hình đồng bộ
        sync_config = self.env['psm.db.sync'].search([
            ('mapping_model_id', '=', self.mapping_model_id.id),
            ('execution_type', '=', 'manual')
        ], limit=1)

        vals = {
            'sync_type': self.sync_type,
            'sync_action': self.sync_action,
            'filter_where_clause': self.filter_where_clause,
            'batch_size': self.batch_size,
            'use_queue': self.use_queue,
            'execution_type': 'manual',
            'active': True,
            'incremental_field': self.incremental_field,
            'last_sync_value': self.last_sync_value if self.sync_type == 'incremental' else False,

        }

        if sync_config:
            sync_config.write(vals)
        else:
            vals.update({
                'name': f"Thủ công: {self.mapping_model_id.name}",
                'mapping_model_id': self.mapping_model_id.id,
            })
            sync_config = self.env['psm.db.sync'].create(vals)

        # Thực hiện đồng bộ
        if self.use_queue:
            # Sử dụng queue_job để chạy trong background
            sync_config.with_delay(description=f"Sync: {sync_config.name}").job_run_sync()
            self.result_message = _('Nhiệm vụ đồng bộ đã được đưa vào hàng đợi và sẽ được thực thi ngay.')
        else:
            # Chạy trực tiếp
            result = sync_config._run_sync()

            if result:
                # Lấy log mới nhất
                last_log = sync_config.last_log_id

                if last_log:
                    self.sync_log_id = last_log.id
                    self.records_created = last_log.records_created
                    self.records_updated = last_log.records_updated
                    self.records_failed = last_log.records_failed
                    self.result_message = last_log.message or _('Đồng bộ thành công!')
                else:
                    self.result_message = _('Đồng bộ thành công!')
            else:
                self.result_message = _('Đồng bộ thất bại. Vui lòng kiểm tra nhật ký lỗi.')

        # Chuyển sang trạng thái kết quả
        self.state = 'result'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_view_log(self):
        """Xem chi tiết nhật ký"""
        self.ensure_one()

        if not self.sync_log_id:
            raise UserError(_('Không có nhật ký để hiển thị.'))

        return {
            'name': _('Chi tiết nhật ký'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.sync.log',
            'view_mode': 'form',
            'res_id': self.sync_log_id.id,
            'target': 'new',
        }

    def action_view_mapped_records(self):
        """Xem bản ghi đã ánh xạ"""
        self.ensure_one()

        if not self.sync_log_id:
            raise UserError(_('Không có dữ liệu để hiển thị.'))

        return {
            'name': _('Bản ghi đã ánh xạ'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.mapping.data',
            'view_mode': 'tree,form',
            'domain': [('log_id', '=', self.sync_log_id.id)],
        }

class PsmDbTestTransformationWizard(models.TransientModel):
    _name = 'psm.db.test.transformation.wizard'
    _description = 'Test Field Transformation Wizard'

    field_mapping_id = fields.Many2one('psm.db.mapping.field', string='Ánh xạ trường', required=True)
    test_input = fields.Text(string='Giá trị kiểm tra', required=True,
                             help="Nhập giá trị để kiểm tra chuyển đổi")
    test_output = fields.Text(string='Kết quả', readonly=True)
    test_error = fields.Text(string='Lỗi', readonly=True)

    def action_test(self):
        """Thực hiện kiểm tra chuyển đổi"""
        self.ensure_one()

        try:
            mapping = self.field_mapping_id
            sync_config = self.env['psm.db.sync'].search([
                ('mapping_model_id', '=', mapping.mapping_model_id.id)
            ], limit=1)

            if not sync_config:
                # Tạo sync config tạm thời
                sync_config = self.env['psm.db.sync'].new({
                    'name': 'Test',
                    'mapping_model_id': mapping.mapping_model_id.id,
                    'sync_type': 'full',
                    'sync_action': 'create_update',
                })

            # Chuẩn bị dữ liệu test
            test_value = self.test_input
            try:
                # Cố gắng parse JSON nếu có thể
                import json
                test_value = json.loads(self.test_input)
            except:
                # Nếu không phải JSON, sử dụng giá trị chuỗi
                pass

            # Tạo source_record giả
            fake_source_record = {mapping.source_field: test_value}

            # Thực hiện chuyển đổi
            result = sync_config._apply_transformation(mapping, test_value, fake_source_record)

            self.test_output = str(result)
            self.test_error = False

        except Exception as e:
            self.test_output = False
            self.test_error = str(e)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.test.transformation.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class PsmDbMetadataWizard(models.TransientModel):
    _name = 'psm.db.metadata.wizard'
    _description = 'Database Metadata Wizard'

    connection_id = fields.Many2one('psm.db.connection', string='Kết nối CSDL', readonly=True)
    metadata = fields.Text(string='Metadata', readonly=True)
    formatted_metadata = fields.Html(string='Thông tin chi tiết', compute='_compute_formatted_metadata')

    @api.depends('metadata')
    def _compute_formatted_metadata(self):
        for record in self:
            if not record.metadata:
                record.formatted_metadata = "<p>Không có metadata</p>"
                continue

            try:
                import json
                data = json.loads(record.metadata)

                html = "<div class='container-fluid'>"

                for table_info in data:
                    table_name = table_info.get('name', 'Unknown')
                    columns = table_info.get('columns', [])
                    primary_keys = table_info.get('primary_keys', [])
                    foreign_keys = table_info.get('foreign_keys', [])

                    html += f"""
                    <div class='card mb-3'>
                        <div class='card-header'>
                            <h5 class='card-title mb-0'>📊 Bảng: {table_name}</h5>
                        </div>
                        <div class='card-body'>
                    """

                    if columns:
                        html += """
                        <h6>🔹 Cột:</h6>
                        <div class='table-responsive'>
                            <table class='table table-sm table-striped'>
                                <thead class='table-dark'>
                                    <tr>
                                        <th>Tên cột</th>
                                        <th>Kiểu dữ liệu</th>
                                        <th>Nullable</th>
                                        <th>Thuộc tính</th>
                                    </tr>
                                </thead>
                                <tbody>
                        """

                        for col in columns:
                            col_name = col.get('name', '')
                            col_type = col.get('type', '')
                            nullable = '✅' if col.get('nullable', True) else '❌'

                            attributes = []
                            if col_name in primary_keys:
                                attributes.append('<span class="badge bg-primary">PK</span>')

                            # Kiểm tra foreign key
                            for fk in foreign_keys:
                                if fk.get('column') == col_name:
                                    ref_table = fk.get('references_table', '')
                                    ref_col = fk.get('references_column', '')
                                    attributes.append(f'<span class="badge bg-info">FK → {ref_table}.{ref_col}</span>')

                            attrs_html = ' '.join(attributes) if attributes else ''

                            html += f"""
                                <tr>
                                    <td><strong>{col_name}</strong></td>
                                    <td><code>{col_type}</code></td>
                                    <td>{nullable}</td>
                                    <td>{attrs_html}</td>
                                </tr>
                            """

                        html += """
                                </tbody>
                            </table>
                        </div>
                        """

                    html += """
                        </div>
                    </div>
                    """

                html += "</div>"
                record.formatted_metadata = html

            except Exception as e:
                record.formatted_metadata = f"<p class='text-danger'>Lỗi hiển thị metadata: {str(e)}</p>"

    def action_create_mapping(self):
        """Tạo ánh xạ từ metadata"""
        self.ensure_one()

        if not self.connection_id or not self.metadata:
            raise UserError(_('Không có dữ liệu để tạo ánh xạ.'))

        return {
            'name': _('Tạo ánh xạ mô hình'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.mapping.model',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_connection_id': self.connection_id.id,
                'metadata_info': self.metadata,
            },
        }