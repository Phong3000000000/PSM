# -*- coding: utf-8 -*-

import logging
import json
import pytz
import hashlib
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PsmDbSync(models.Model):
    _name = 'psm.db.sync'
    _description = 'Nhiệm vụ đồng bộ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'connection_id, target_model_id'

    name = fields.Char(string='Tên nhiệm vụ', compute='_compute_name', store=True, index=True)
    sequence = fields.Integer(string='Thứ tự', default=10, help="Thứ tự thực hiện các nhiệm vụ")

    # Thông tin mapping
    mapping_model_id = fields.Many2one('psm.db.mapping.model', string='Ánh xạ mô hình',
                                       required=True, tracking=True, ondelete='cascade')
    connection_id = fields.Many2one(related='mapping_model_id.connection_id', string='Kết nối CSDL',
                                    store=True, readonly=True)
    target_model_id = fields.Many2one(related='mapping_model_id.target_model_id', string='Model đích',
                                      store=True, readonly=True)
    target_model = fields.Char(related='mapping_model_id.target_model_id.model', string='Tên Model đích',
                               readonly=True)

    # Điều kiện đồng bộ
    filter_domain = fields.Char(string='Bộ lọc Odoo', default='[]',
                                help="Domain để lọc bản ghi đích (JSON format)")
    filter_where_clause = fields.Text(string='Điều kiện SQL',
                                      help="Mệnh đề WHERE SQL áp dụng với bảng/truy vấn nguồn (không cần WHERE)")
    incremental_field = fields.Char(string='Trường tăng dần', default='write_date',
                                    help="Trường dùng cho đồng bộ tăng dần (thường là last_update, update_date)")
    last_sync_value = fields.Char(string='Giá trị đồng bộ cuối')

    # Cấu hình đồng bộ
    sync_type = fields.Selection([
        ('full', 'Đầy đủ'),
        ('incremental', 'Tăng dần')
    ], string='Kiểu đồng bộ', default='full', required=True, tracking=True)

    sync_action = fields.Selection([
        ('create_update', 'Tạo và cập nhật'),
        ('create_only', 'Chỉ tạo mới'),
        ('update_only', 'Chỉ cập nhật'),
    ], string='Hành động', default='create_update', required=True, tracking=True)

    execution_type = fields.Selection([
        ('scheduled', 'Lên lịch'),
        ('manual', 'Thủ công'),
    ], string='Kiểu thực thi', default='manual', required=True, tracking=True)

    # Các mốc thời gian đồng bộ
    cron_id = fields.Many2one('ir.cron', string='Nhiệm vụ định kỳ',
                              help="Cron job đồng bộ định kỳ")
    interval_number = fields.Integer(string='Lặp lại mỗi', default=1,
                                     compute='_compute_cron_info', store=True, readonly=False)
    interval_type = fields.Selection([
        ('minutes', 'Phút'),
        ('hours', 'Giờ'),
        ('days', 'Ngày'),
        ('weeks', 'Tuần'),
        ('months', 'Tháng')
    ], string='Đơn vị thời gian', default='hours', compute='_compute_cron_info', store=True, readonly=False)
    nextcall = fields.Datetime(string='Lần chạy tiếp theo', related='cron_id.nextcall')

    # Thông số hiệu năng
    batch_size = fields.Integer(string='Kích thước lô', default=50, required=True,
                                help="Số bản ghi xử lý trong mỗi lô")
    timeout = fields.Integer(string='Thời gian chờ (giây)', default=300, required=True,
                             help="Thời gian tối đa cho mỗi lần đồng bộ")
    retries = fields.Integer(string='Số lần thử lại', default=3, required=True)
    use_queue = fields.Boolean(string='Sử dụng hàng đợi', default=True,
                               help="Sử dụng cơ chế hàng đợi (queue_job) để xử lý đồng bộ trong background")

    # Xử lý nâng cao
    pre_sync_hook = fields.Text(string='Hook trước đồng bộ',
                                help="Mã Python thực thi trước khi đồng bộ")
    post_sync_hook = fields.Text(string='Hook sau đồng bộ',
                                 help="Mã Python thực thi sau khi đồng bộ")
    use_checksum = fields.Boolean(string='Dùng checksum', default=False,
                                  help="Dùng checksum để phát hiện thay đổi")

    # Thông tin trạng thái
    active = fields.Boolean(string='Đang hoạt động', default=True, tracking=True)
    state = fields.Selection([
        ('ready', 'Sẵn sàng'),
        ('running', 'Đang chạy'),
        ('paused', 'Tạm dừng'),
        ('error', 'Lỗi')
    ], string='Trạng thái', default='ready', tracking=True)

    # Thống kê
    last_sync_date = fields.Datetime(string='Đồng bộ gần nhất', readonly=True, tracking=True)
    last_duration = fields.Float(string='Thời gian xử lý (giây)', readonly=True)
    last_log_id = fields.Many2one('psm.db.sync.log', string='Nhật ký gần nhất', readonly=True)

    # Metrics
    success_count = fields.Integer(string='Thành công', default=0, readonly=True,
                                   help="Tổng số lần đồng bộ thành công")
    error_count = fields.Integer(string='Lỗi', default=0, readonly=True,
                                 help="Tổng số lần đồng bộ thất bại")
    total_records_synced = fields.Integer(string='Bản ghi đã đồng bộ', default=0, readonly=True)
    total_records_failed = fields.Integer(string='Bản ghi lỗi', default=0, readonly=True)
    avg_duration = fields.Float(string='Thời gian trung bình (giây)', default=0, readonly=True)

    # Relations
    log_ids = fields.One2many('psm.db.sync.log', 'sync_id', string='Nhật ký đồng bộ')
    log_count = fields.Integer(compute='_compute_log_count', string='Số lượng nhật ký')
    mapped_record_ids = fields.One2many('psm.db.mapping.data', 'sync_id', string='Bản ghi đã ánh xạ')
    mapped_record_count = fields.Integer(compute='_compute_mapped_record_count',
                                         string='Số lượng bản ghi')

    # System fields
    company_id = fields.Many2one('res.company', string='Công ty',
                                 required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Người phụ trách',
                              default=lambda self: self.env.user, tracking=True)

    @api.depends('execution_type', 'connection_id.name', 'target_model_id.name')
    def _compute_name(self):
        for record in self:
            execution_type = dict(self._fields['execution_type'].selection).get(record.execution_type, '')
            record.name = f"{execution_type} đồng bộ {record.connection_id.name}: {record.target_model_id.name}"

    @api.depends('cron_id', 'cron_id.interval_type', 'cron_id.interval_number')
    def _compute_cron_info(self):
        for record in self.filtered(lambda x: x.cron_id):
            record.interval_type = record.cron_id.interval_type
            record.interval_number = record.cron_id.interval_number

    @api.depends('log_ids')
    def _compute_log_count(self):
        for record in self:
            record.log_count = len(record.log_ids)

    @api.depends('mapped_record_ids')
    def _compute_mapped_record_count(self):
        for record in self:
            record.mapped_record_count = len(record.mapped_record_ids)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.execution_type == 'scheduled':
            res._create_cron_job()
        return res

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if 'execution_type' in vals and vals['execution_type'] == 'scheduled':
                if not record.cron_id:
                    record._create_cron_job()
            if record.cron_id and any(f in vals for f in ['active']):
                record._update_cron_job()
            if 'execution_type' in vals and vals['execution_type'] != 'scheduled' and record.cron_id:
                record._delete_cron_job()
        return res

    def unlink(self):
        for record in self:
            if record.cron_id:
                record._delete_cron_job()
            record.log_ids = False
        return super().unlink()

    def _create_cron_job(self):
        self.ensure_one()
        if not self.interval_number or not self.interval_type:
            return
        vals = self._prepare_cron_values()
        cron = self.env['ir.cron'].sudo().create(vals)
        self.cron_id = cron.id

    def _update_cron_job(self):
        self.ensure_one()
        if not self.cron_id:
            return
        vals = self._prepare_cron_values()
        self.cron_id.sudo().write(vals)

    def _delete_cron_job(self):
        self.ensure_one()
        if self.cron_id:
            self.cron_id.sudo().unlink()
            self.cron_id = False

    def _prepare_cron_values(self):
        self.ensure_one()

        vals = {
            'name': f"Sync: {self.name} ({self.mapping_model_id.name})",
            'model_id': self.env['ir.model']._get('psm.db.sync').id,
            'state': 'code',
            'code': f"model.browse({self.id})._run_sync()",
            'interval_number': self.interval_number,
            'interval_type': self.interval_type,
            'numbercall': -1,
            'doall': False,
            'active': self.active,
            'user_id': self.env.ref('base.user_root').id,
        }

        return vals

    def action_sync_now(self):
        self.ensure_one()
        if self.state == 'running':
            raise UserError(_('Nhiệm vụ đồng bộ đang chạy. Vui lòng chờ cho đến khi hoàn thành.'))

        if self.use_queue:
            self.with_delay(description=f"Sync: {self.name}").job_run_sync()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Đã lên lịch'),
                    'message': _('Nhiệm vụ đồng bộ đã được đưa vào hàng đợi và sẽ được thực thi ngay.'),
                    'sticky': False,
                    'type': 'success'
                }
            }
        else:
            return self._run_sync()

    def action_reset_sync(self):
        self.ensure_one()
        if self.state == 'running':
            raise UserError(_('Không thể đặt lại khi nhiệm vụ đang chạy.'))
        self.write({
            'state': 'ready',
            'last_sync_value': False
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã đặt lại'),
                'message': _('Nhiệm vụ đồng bộ đã được đặt lại thành công.'),
                'sticky': False,
                'type': 'success'
            }
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Nhật ký đồng bộ'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.sync.log',
            'view_mode': 'tree,form',
            'domain': [('sync_id', '=', self.id)],
            'context': {'default_sync_id': self.id},
        }

    def action_view_mapped_records(self):
        self.ensure_one()
        return {
            'name': _('Bản ghi đã ánh xạ'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.mapping.data',
            'view_mode': 'tree,form',
            'domain': [('sync_id', '=', self.id)],
            'context': {'default_sync_id': self.id},
        }

    def job_run_sync(self):
        return self._run_sync()

    def _run_sync(self):
        self.ensure_one()

        mapping_errors = self.mapping_model_id.action_check_mapping_ready_for_sync()
        if mapping_errors:
            error_msg = "Mapping chưa sẵn sàng:\n" + '\n'.join(mapping_errors)
            _logger.error("Sync validation failed: %s", error_msg)
            self.write({'state': 'error'})
            raise UserError(error_msg)

        if not self.mapping_model_id or not self.mapping_model_id.connection_id:
            raise UserError(_('Vui lòng cấu hình ánh xạ mô hình và kết nối CSDL.'))

        if self.state == 'running':
            _logger.warning("Nhiệm vụ đồng bộ %s đang chạy, bỏ qua yêu cầu mới.", self.name)
            return False

        start_time = fields.Datetime.now()
        self.write({'state': 'running'})

        log_vals = {
            'sync_id': self.id,
            'mapping_model_id': self.mapping_model_id.id,
            'start_time': start_time,
            'status': 'running',
        }
        log = self.env['psm.db.sync.log'].create(log_vals)
        # self.env.cr.commit()
        try:
            if self.pre_sync_hook:
                self._execute_hook(self.pre_sync_hook, log)

            source_data = self._get_source_data(log)

            if not source_data:
                log.write({
                    'status': 'completed',
                    'end_time': fields.Datetime.now(),
                    'records_found': 0,
                    'records_created': 0,
                    'records_updated': 0,
                    'message': _('Không có dữ liệu nào được tìm thấy.')
                })
                self.write({
                    'state': 'ready',
                    'last_sync_date': fields.Datetime.now(),
                    'last_duration': (fields.Datetime.now() - start_time).total_seconds(),
                    'last_log_id': log.id,
                    'success_count': self.success_count + 1,
                })
                return True

            result = self._process_data(source_data, log)

            log.write({
                'status': 'completed',
                'end_time': fields.Datetime.now(),
                'records_found': len(source_data),
                'records_created': result.get('created', 0),
                'records_updated': result.get('updated', 0),
                'records_failed': result.get('failed', 0),
                'message': result.get('message', '')
            })

            duration = (fields.Datetime.now() - start_time).total_seconds()
            total_syncs = self.success_count + 1
            new_avg_duration = ((self.avg_duration * self.success_count) + duration) / total_syncs

            last_sync_value = False
            if self.sync_type == 'incremental' and self.incremental_field and source_data:
                last_sync_value = max([record.get(self.incremental_field) for record in source_data if
                                       record.get(self.incremental_field)])

            self.write({
                'state': 'ready',
                'last_sync_date': fields.Datetime.now(),
                'last_duration': duration,
                'last_log_id': log.id,
                'success_count': total_syncs,
                'total_records_synced': self.total_records_synced + result.get('created', 0) + result.get('updated', 0),
                'total_records_failed': self.total_records_failed + result.get('failed', 0),
                'avg_duration': new_avg_duration,
                'last_sync_value': last_sync_value if last_sync_value else self.last_sync_value
            })

            if self.post_sync_hook:
                self._execute_hook(self.post_sync_hook, log)

            return True

        except Exception as e:
            error_msg = str(e)
            _logger.error("Lỗi khi đồng bộ %s: %s", self.name, error_msg)
            log.write({
                'status': 'failed',
                'end_time': fields.Datetime.now(),
                'message': error_msg
            })
            self.write({
                'state': 'error',
                'last_duration': (fields.Datetime.now() - start_time).total_seconds(),
                'last_log_id': log.id,
                'error_count': self.error_count + 1
            })
            return False

    def _get_source_data(self, log):
        self.ensure_one()
        mapping_model = self.mapping_model_id
        connection = mapping_model.connection_id

        try:
            if mapping_model.source_type == 'table':
                base_query = f"SELECT * FROM {mapping_model.source_table}"
            else:
                base_query = f"SELECT * FROM ({mapping_model.source_query}) query_result"

            where_conditions = []
            params = {}

            if self.filter_where_clause:
                where_conditions.append(f"({self.filter_where_clause})")

            if self.sync_type == 'incremental' and self.incremental_field and self.last_sync_value:
                where_conditions.append(f"{self.incremental_field} >= :last_sync_value")
                params['last_sync_value'] = self.last_sync_value

            if where_conditions:
                if 'WHERE' in base_query.upper() and mapping_model.source_type == 'table':
                    query = f"{base_query} AND {' AND '.join(where_conditions)}"
                else:
                    query = f"{base_query} WHERE {' AND '.join(where_conditions)}"
            else:
                query = base_query

            if self.sync_type == 'incremental' and self.incremental_field:
                # if 'ORDER BY' in query.upper():
                #     query = f"{query}, {self.incremental_field} ASC"
                # else:
                query = f"{query} ORDER BY {self.incremental_field} ASC"

            # Xử lý LIMIT theo từng loại database
            if self.batch_size > 0:
                db_type = connection.db_type

                if db_type in ['mysql', 'mariadb', 'postgresql']:
                    query = f"{query} LIMIT {self.batch_size}"
                elif db_type == 'mssql':
                    # Với MSSQL, cần sử dụng TOP hoặc OFFSET...FETCH
                    # if 'ORDER BY' in query.upper():
                    #     # Nếu có ORDER BY, sử dụng OFFSET...FETCH (SQL Server 2012+)
                    #     query = f"{query} OFFSET 0 ROWS FETCH NEXT {self.batch_size} ROWS ONLY"
                    # else:
                    # Nếu không có ORDER BY, sử dụng TOP
                    # Cần chèn TOP ngay sau SELECT
                    if query.upper().startswith('SELECT '):
                        query = query.replace('SELECT ', f'SELECT TOP {self.batch_size} ', 1)
                    elif query.upper().startswith('SELECT\t') or query.upper().startswith('SELECT\n'):
                        query = query.replace('SELECT', f'SELECT TOP {self.batch_size}', 1)
                elif db_type == 'oracle':
                    # Oracle sử dụng ROWNUM hoặc FETCH FIRST (Oracle 12c+)
                    if 'ORDER BY' in query.upper():
                        # Oracle 12c+ syntax
                        query = f"{query} FETCH FIRST {self.batch_size} ROWS ONLY"
                    else:
                        # Older Oracle syntax with ROWNUM
                        query = f"SELECT * FROM ({query}) WHERE ROWNUM <= {self.batch_size}"

            if mapping_model.source_query_with_recursive:
                query = f"{mapping_model.source_query_with_recursive.strip().rstrip(';')} {query}"
            _logger.info("Executing query: %s with params: %s", query, params)
            result = connection.execute_query(query, params)
            return result

        except Exception as e:
            log.write({'message': f"Lỗi khi lấy dữ liệu: {str(e)}"})
            raise

    def _process_data(self, source_data, log):
        """
        Cải tiến process data - giữ nguyên logic checksum + tối ưu relation sync
        """
        self.ensure_one()
        mapping_model = self.mapping_model_id
        target_model = mapping_model.target_model

        if not target_model or not source_data:
            return {'created': 0, 'updated': 0, 'failed': 0, 'message': 'Không có dữ liệu để xử lý'}

        stats = {'created': 0, 'updated': 0, 'failed': 0, 'failures': [], 'linked': 0}

        field_mappings = self.env['psm.db.mapping.field'].search([
            ('mapping_model_id', '=', mapping_model.id),
            ('active', '=', True),
            ('include_in_sync', '=', True),
            ('target_field', '!=', False)
        ])

        self._pre_sync_relations(source_data, field_mappings)

        for source_record in source_data:
            try:
                source_key_field = mapping_model.source_key_field
                source_key_value = source_record.get(source_key_field)

                if not source_key_value:
                    stats['failed'] += 1
                    stats['failures'].append(f"Không tìm thấy giá trị khóa {source_key_field} trong bản ghi nguồn")
                    continue

                checksum = False
                mapping_data = False
                if self.use_checksum or mapping_model.use_checksum:
                    checksum = self._calculate_checksum(source_record)
                    mapping_data = False

                    mapping_datas = self.env['psm.db.mapping.data'].search([
                        ('mapping_model_id', '=', mapping_model.id),
                        ('model', '=', target_model), ('field', '=', mapping_model.target_key_field),
                        ('source_field', '=', mapping_model.source_key_field), ('source_id', '=', str(source_key_value))
                    ])

                    for data in mapping_datas:
                        if data.res_id and self.env[target_model].browse(data.res_id).exists():
                            mapping_data = data
                            break

                    # Xóa tất cả mapping không hợp lệ
                    invalid_mappings = mapping_datas.filtered(lambda x: x != mapping_data)
                    invalid_mappings.unlink()

                    # QUAN TRỌNG: Bỏ qua bản ghi nếu checksum không thay đổi
                    if mapping_data and self.use_checksum and mapping_data.checksum == checksum:
                        _logger.debug("Bỏ qua bản ghi %s - checksum không thay đổi", source_key_value)
                        continue

                # Chuyển đổi dữ liệu từ nguồn sang định dạng Odoo
                target_values, one2many_cache = self._transform_record(source_record, field_mappings)

                # Tìm bản ghi đích đã tồn tại
                existing_target_record = self._find_existing_record(mapping_model, source_key_value)
                if existing_target_record:
                    # CẬP NHẬT bản ghi có sẵn
                    if self.sync_action in ('create_update', 'update_only'):
                        self._update_target_record(existing_target_record, target_values, stats)
                        mapping_data = True
                else:
                    # TẠO MỚI bản ghi
                    if self.sync_action in ('create_update', 'create_only'):
                        existing_target_record = self._create_target_record(target_model, target_values,
                                                                            source_key_value, stats)
                        mapping_data = True

                if existing_target_record and one2many_cache:
                    self._process_one2many_cache(one2many_cache, existing_target_record)

                # Tạo/cập nhật dữ liệu ánh xạ để theo dõi mối quan hệ
                if existing_target_record and mapping_data:
                    self.env['psm.db.mapping.data'].create_or_update_mapping(
                        mapping_model_id=mapping_model.id,
                        model=target_model,
                        field=mapping_model.target_key_field,
                        res_id=existing_target_record.id,
                        source_id=str(source_key_value),
                        source_model=mapping_model.source_table if mapping_model.source_type == 'table' else 'query',
                        source_field=mapping_model.source_key_field,
                        checksum=checksum,
                        sync_id=self.id,
                        log_id=log.id
                    )
                    stats['linked'] += 1

            except UserError:
                raise
            except Exception as e:
                stats['failed'] += 1
                error_msg = f"Lỗi xử lý bản ghi {source_key_value if 'source_key_value' in locals() else 'N/A'}: {str(e)}"
                stats['failures'].append(error_msg)
                _logger.error(error_msg)

        # Tạo thông báo kết quả đồng bộ
        message = f"Đồng bộ hoàn tất: {stats['created']} tạo mới, {stats['updated']} cập nhật, {stats['linked']} liên kết, {stats['failed']} lỗi"
        if stats['failures']:
            message += f"\nChi tiết lỗi: {'; '.join(stats['failures'][:5])}"
            if len(stats['failures']) > 5:
                message += f" và {len(stats['failures']) - 5} lỗi khác"

        stats['message'] = message
        return stats

    def _pre_sync_relations(self, source_data, field_mappings):
        """
        Thu thập và đồng bộ tất cả quan hệ thiếu TRƯỚC KHI xử lý dữ liệu chính
        Tránh tạo quá nhiều sync task bằng cách batch sync theo mapping
        """
        # Nhóm các quan hệ thiếu theo mapping
        missing_relations = {}

        # Lọc chỉ các field mapping là quan hệ và có tự động tạo
        relation_mappings = [fm for fm in field_mappings
                             if fm.transformation_type == 'relation'
                             and fm.relation_create_auto
                             and fm.relation_model_id]

        if not relation_mappings:
            _logger.debug("Không có quan hệ nào cần đồng bộ tự động")
            return

        # Thu thập tất cả giá trị thiếu cho mỗi relation mapping
        for mapping in relation_mappings:
            relation_mapping = mapping.relation_model_id
            missing_values = set()

            for source_record in source_data:
                source_value = source_record.get(mapping.source_field)
                if not source_value:
                    continue

                # Xử lý many2many
                if mapping.target_field_type == 'many2many':
                    values = self._parse_m2m_values(source_value)
                    for val in values:
                        if not self._find_existing_record(relation_mapping, val):
                            missing_values.add(str(val))
                elif mapping.target_field_type == 'one2many':
                    # values = self._parse_one2many_values(source_value)
                    # for val in values:
                    #     if not self._find_existing_record(relation_mapping, val):
                    #         missing_values.add(str(val))
                    continue
                else:
                    # Xử lý many2one
                    if not self._find_existing_record(relation_mapping, source_value):
                        missing_values.add(str(source_value))

            if missing_values:
                missing_relations[relation_mapping.id] = {
                    'mapping': relation_mapping,
                    'values': list(missing_values),
                    'field_name': mapping.target_field
                }

        # Đồng bộ tất cả quan hệ thiếu - CHỈ TẠO 1 TASK CHO MỖI MAPPING
        for relation_id, data in missing_relations.items():
            try:
                _logger.info("Đồng bộ trước %d quan hệ thiếu cho %s (trường: %s)",
                             len(data['values']), data['mapping'].name, data['field_name'])

                # ✅ SỬ DỤNG method có sẵn với TẤT CẢ values cùng lúc
                temp_sync = self._create_temp_sync_for_relation(data['mapping'], data['values'])

                # Thực thi đồng bộ
                sync_result = temp_sync._run_sync()
                if sync_result:
                    _logger.info("Đồng bộ quan hệ thành công cho %s: %d bản ghi",
                                 data['mapping'].name, len(data['values']))
                else:
                    _logger.warning("Đồng bộ quan hệ thất bại cho %s", data['mapping'].name)

                # Xóa sync task tạm để không làm rối database
                temp_sync.unlink()

            except Exception as e:
                _logger.error("Lỗi đồng bộ quan hệ cho %s: %s", data['mapping'].name, str(e))

    def _parse_m2m_values(self, source_value):
        """
        Phân tích giá trị many2many từ chuỗi hoặc list

        Args:
            source_value: Giá trị nguồn (string, list, hoặc single value)

        Returns:
            list: Danh sách các giá trị đã được xử lý
        """
        if not source_value:
            return []

        if isinstance(source_value, str):
            # Xử lý chuỗi có dấu phẩy: "1,2,3" hoặc "value1, value2"
            if ',' in source_value:
                return [v.strip() for v in source_value.split(',') if v.strip()]
            else:
                return [source_value.strip()]
        elif isinstance(source_value, list):
            # Xử lý list: [1, 2, 3] hoặc ['a', 'b', 'c']
            return [str(v) for v in source_value if v]
        else:
            # Xử lý giá trị đơn: 123 hoặc 'single_value'
            return [str(source_value)]

    def _find_existing_record(self, mapping_model, source_key_value):
        if not source_key_value:
            return False

        target_model = mapping_model.target_model
        target_key_field = mapping_model.target_key_field

        # Trường hợp đặc biệt: tìm theo ID
        if target_key_field == 'id':
            try:
                existing = self.env[target_model].browse(int(source_key_value))
                if existing.exists():
                    return existing
            except (ValueError, TypeError):
                pass  # source_key_value không phải số

        # Validate target key field tồn tại
        field_info = self.env[target_model]._fields.get(target_key_field)
        if not field_info:
            raise UserError(
                _('Trường khóa đích "%s" không tồn tại trong model "%s"') % (target_key_field, target_model))

        # Tìm theo target key field
        existing = self.env[target_model].search([
            (target_key_field, '=', source_key_value)
        ], limit=1)

        return existing if existing else False

    def _create_target_record(self, target_model, target_values, source_key_value, stats):
        try:
            new_record = self.env[target_model].create(target_values)
            stats['created'] += 1
            return new_record
        except Exception as e:
            # self.env.cr.rollback()
            stats['failed'] += 1
            error_msg = f"Lỗi tạo bản ghi {target_model} từ nguồn {source_key_value}: {str(e)}"
            stats['failures'].append(error_msg)
            _logger.error(error_msg)
            error_msg = f"Lỗi tạo bản ghi {target_model} từ nguồn {source_key_value}: {str(target_values)}"
            raise UserError(error_msg)

    def _update_target_record(self, target_record, target_values, stats):
        try:
            target_record.write(target_values)
            stats['updated'] += 1
        except Exception as e:
            # self.env.cr.rollback()
            stats['failed'] += 1
            error_msg = f"Lỗi cập nhật bản ghi {target_record._name} (ID: {target_record.id}): {str(e)}"
            stats['failures'].append(error_msg)
            _logger.error(error_msg)
            error_msg = f"Lỗi cập nhật bản ghi {target_record._name} (ID: {target_record.id}): {str(target_values)}"
            raise UserError(error_msg)

    def _transform_record(self, source_record, field_mappings):
        target_values = {}
        one2many_cache = {}
        sorted_mappings = sorted(field_mappings, key=lambda m: m.sequence)

        for mapping in sorted_mappings:
            source_field = mapping.source_field
            target_field = mapping.target_field

            if not target_field:
                continue

            source_value = source_record.get(source_field)

            if mapping.skip_if_empty and (source_value is None or source_value == ''):
                continue

            try:
                if (mapping.transformation_type == 'relation' and
                        mapping.target_field_type == 'one2many'):
                    one2many_cache[target_field] = {
                        'mapping': mapping,
                        'source_value': source_value,
                        'source_record': source_record
                    }
                    continue

                converted_value = self._apply_transformation(mapping, source_value, source_record)

                if converted_value is not None:
                    if mapping.trim_whitespace and isinstance(converted_value, str):
                        converted_value = converted_value.strip()

                    if mapping.force_uppercase and isinstance(converted_value, str):
                        converted_value = converted_value.upper()
                    elif mapping.force_lowercase and isinstance(converted_value, str):
                        converted_value = converted_value.lower()

                if (converted_value is None or converted_value == '') and mapping.default_value:
                    converted_value = mapping.default_value

                # Xử lý đặc biệt cho trường date/datetime với giá trị None
                if mapping.target_field_type in ('date', 'datetime'):
                    if converted_value is None or converted_value == '':
                        converted_value = False
                elif mapping.convert_empty_to_false:
                    if converted_value is None or converted_value == '':
                        converted_value = False

                if mapping.skip_if_empty and not converted_value:
                    continue

                target_values[target_field] = converted_value
            except UserError:
                raise
            except Exception as e:
                _logger.error("Lỗi chuyển đổi trường %s: %s", source_field, str(e))
                if mapping.default_value:
                    target_values[target_field] = mapping.default_value
                else:
                    # Đặt giá trị mặc định theo kiểu field
                    if mapping.target_field_type in ('date', 'datetime'):
                        target_values[target_field] = False
                    elif mapping.target_field_type in ('integer', 'float', 'monetary'):
                        target_values[target_field] = 0
                    elif mapping.target_field_type == 'boolean':
                        target_values[target_field] = False
                    else:
                        target_values[target_field] = False

        return target_values, one2many_cache

    def _apply_transformation(self, mapping, source_value, source_record):
        if source_value is None:
            return None
        target_field = mapping.target_field
        transformation_type = mapping.transformation_type

        if transformation_type == 'direct':
            return source_value

        elif transformation_type == 'date_format':
            if not source_value:
                return False
            try:
                if isinstance(source_value, datetime):
                    dt_value = source_value
                else:
                    dt_value = datetime.strptime(str(source_value), mapping.source_date_format or '%Y-%m-%d %H:%M:%S')
                if mapping.target_date_format:
                    return dt_value.strftime(mapping.target_date_format)
                return dt_value
            except Exception as e:
                _logger.error("Lỗi chuyển đổi ngày %s: %s", source_value, str(e))
                return False

        elif transformation_type == 'number_format':
            if source_value == '' or source_value is None:
                return 0.0
            try:
                if isinstance(source_value, str):
                    if mapping.decimal_separator != '.':
                        source_value = source_value.replace(mapping.decimal_separator, '.')
                    if mapping.thousands_separator:
                        source_value = source_value.replace(mapping.thousands_separator, '')
                num_value = float(source_value)
                if mapping.round_precision is not None:
                    num_value = round(num_value, mapping.round_precision)
                return num_value
            except Exception as e:
                _logger.error("Lỗi chuyển đổi số %s: %s", source_value, str(e))
                return 0.0

        elif transformation_type == 'mapping':
            if not mapping.value_mapping:
                return source_value
            try:
                mapping_dict = json.loads(mapping.value_mapping)
                str_value = str(source_value)
                if str_value in mapping_dict:
                    return mapping_dict[str_value]
                return source_value
            except Exception as e:
                _logger.error("Lỗi ánh xạ giá trị %s: %s", source_value, str(e))
                return source_value

        elif transformation_type == 'function':
            if not mapping.python_function:
                return source_value
            try:
                local_vars = {'value': source_value, 'source_record': source_record}
                exec(mapping.python_function, globals(), local_vars)
                if 'transform_value' in local_vars:
                    return local_vars['transform_value'](source_value, source_record)
                return source_value
            except Exception as e:
                _logger.error("Lỗi thực thi hàm Python: %s", str(e))
                return source_value

        elif transformation_type == 'relation':
            if not mapping.relation_model_id:
                # Kiểm tra nếu là many2many field mà không có relation_model_id
                if mapping.target_field_type == 'many2many':
                    return self._handle_many2many_direct(source_value)
                return False

            try:
                # Kiểm tra target field type để xử lý khác nhau
                if mapping.target_field_type == 'many2many':
                    return self._handle_many2many_relation(mapping, source_value)
                elif mapping.target_field_type == 'one2many':
                    return self._handle_one2many_relation(mapping, source_value)
                else:
                    # Logic many2one hiện tại của bạn
                    return self._handle_many2one_relation(mapping, source_value)
            except UserError:
                raise
            except Exception as e:
                _logger.error("Lỗi xử lý quan hệ %s: %s", source_value, str(e))
                return False

        elif transformation_type == 'static':
            return mapping.static_value

        return source_value

    def _handle_many2one_relation(self, mapping, source_value):
        if not source_value:
            return False

        relation_mapping = mapping.relation_model_id
        if not relation_mapping:
            _logger.warning("Không tìm thấy relation mapping cho trường %s", mapping.target_field)
            return False

        # Tìm bản ghi quan hệ (should exist after pre-sync)
        existing_record_id = self._find_existing_record(relation_mapping, source_value)
        if existing_record_id:
            return existing_record_id.id

        # Nếu không tìm thấy và là trường bắt buộc
        if self._is_field_required(mapping):
            raise UserError(
                _('Không tìm thấy bản ghi quan hệ cho trường bắt buộc "%s" với giá trị "%s". '
                  'Vui lòng kiểm tra dữ liệu nguồn hoặc cấu hình ánh xạ.') %
                (mapping.target_field, source_value))

        _logger.debug("Không tìm thấy quan hệ cho %s = %s, bỏ qua", mapping.target_field, source_value)
        return False

    def _handle_many2many_relation(self, mapping, source_values):
        if not source_values:
            return []

        # Parse source values thành list
        values = self._parse_m2m_values(source_values)
        if not values:
            return []

        relation_mapping = mapping.relation_model_id
        if not relation_mapping:
            _logger.warning("Không tìm thấy relation mapping cho trường %s", mapping.target_field)
            return []

        target_ids = []
        missing_values = []

        # Tìm tất cả records đã tồn tại (should exist after pre-sync)
        for source_value in values:
            existing_record_id = self._find_existing_record(relation_mapping, source_value)
            if existing_record_id:
                target_ids.append(existing_record_id.id)
            else:
                missing_values.append(source_value)

        # Log các giá trị không tìm thấy
        if missing_values:
            _logger.warning("Không tìm thấy %d quan hệ many2many cho trường %s: %s",
                            len(missing_values), mapping.target_field, missing_values[:5])

        # Trả về định dạng many2many của Odoo: [(6, 0, [ids])]
        return [(6, 0, target_ids)] if target_ids else []

    def _handle_many2many_direct(self, source_value):
        """Xử lý many2many trực tiếp (không qua relation mapping)"""

        if not source_value:
            return []

        try:
            # Parse source value thành list of IDs
            if isinstance(source_value, list):
                ids = []
                for item in source_value:
                    try:
                        if isinstance(item, int):
                            ids.append(item)
                        elif isinstance(item, str) and item.isdigit():
                            ids.append(int(item))
                    except:
                        continue
                return [(6, 0, ids)] if ids else []

            elif isinstance(source_value, str):
                if ',' in source_value:
                    # "1,2,3"
                    parts = source_value.split(',')
                    ids = []
                    for part in parts:
                        try:
                            clean_part = part.strip()
                            if clean_part.isdigit():
                                ids.append(int(clean_part))
                        except:
                            continue
                    return [(6, 0, ids)] if ids else []

                elif source_value.isdigit():
                    # "5"
                    return [(6, 0, [int(source_value)])]

                else:
                    # Try JSON
                    import json
                    try:
                        parsed = json.loads(source_value)
                        if isinstance(parsed, list):
                            ids = [int(x) for x in parsed if str(x).isdigit()]
                            return [(6, 0, ids)] if ids else []
                    except:
                        pass
                    return []

            elif isinstance(source_value, int):
                return [(6, 0, [source_value])]

            else:
                return []

        except Exception as e:
            _logger.error(f"Error handling many2many direct: {str(e)}")
            return []

    def _transform_child_record(self, child_data, relation_mapping):
        """
        Transform child record - SỬ DỤNG LẠI _transform_record có sẵn của bạn
        """
        try:
            # Lấy field mappings cho relation
            field_mappings = self.env['psm.db.mapping.field'].search([
                ('mapping_model_id', '=', relation_mapping.id),
                ('active', '=', True),
                ('include_in_sync', '=', True),
                ('target_field', '!=', False)
            ])

            # SỬ DỤNG LẠI method _transform_record có sẵn
            return self._transform_record(child_data, field_mappings)

        except Exception as e:
            _logger.error("Lỗi transform child record: %s", str(e))
            return {}

    def _calculate_checksum(self, record):
        sorted_data = {k: record[k] for k in sorted(record.keys())}

        for key, value in sorted_data.items():
            if value is not None and not isinstance(value, (str, int, float, bool)):
                sorted_data[key] = str(value)

        data_str = json.dumps(sorted_data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _execute_hook(self, hook_code, log):
        try:
            local_vars = {
                'self': self,
                'log': log,
                'env': self.env,
                'mapping_model': self.mapping_model_id,
                'connection': self.mapping_model_id.connection_id,
                'target_model': self.mapping_model_id.target_model,
                'datetime': datetime,
                'timedelta': timedelta,
            }

            exec(hook_code, globals(), local_vars)
            return True
        except Exception as e:
            error_msg = f"Lỗi thực thi hook: {str(e)}"
            _logger.error(error_msg)
            log.write({
                'message': (log.message or '') + '\n' + error_msg
            })
            return False

    def _create_temp_sync_for_relation(self, relation_mapping, source_values):
        key_field = relation_mapping.source_key_field
        if len(source_values) == 1:
            where_clause = f"{key_field} = '{source_values[0]}'"
        else:
            # Multiple values
            values_str = "','".join([str(v) for v in source_values])
            where_clause = f"{key_field} IN ('{values_str}')"

        # Tạo temp sync task
        temp_sync = self.env['psm.db.sync'].create({
            'name': f'Tự động đồng bộ quan hệ: {relation_mapping.name}',
            'mapping_model_id': relation_mapping.id,
            'sync_type': 'full',
            'sync_action': 'create_update',
            'filter_where_clause': where_clause,
            'batch_size': 0,
            'use_queue': False,
            'execution_type': 'manual'
        })

        _logger.info("Tạo sync task tạm thời cho relation: %s với điều kiện: %s",
                     relation_mapping.name, where_clause)
        return temp_sync

    def _is_field_required(self, mapping):
        try:
            target_model = mapping.mapping_model_id.target_model
            if target_model in self.env:
                field_info = self.env[target_model]._fields.get(mapping.target_field)
                is_required = getattr(field_info, 'required', False)
                if is_required:
                    _logger.debug("Trường %s.%s là bắt buộc", target_model, mapping.target_field)
                return is_required
        except Exception as e:
            _logger.warning("Lỗi kiểm tra trường bắt buộc: %s", str(e))
        return False

    def _process_one2many_cache(self, one2many_cache, parent_record):
        """
        Xử lý one2many fields SAU KHI đã tạo parent record
        """
        for field_name, cache_data in one2many_cache.items():
            try:
                mapping = cache_data['mapping']
                source_value = cache_data['source_value']

                if not source_value or not mapping.relation_model_id:
                    continue

                _logger.debug("Xử lý one2many field %s cho parent record ID %d",
                              field_name, parent_record.id)

                # Parse one2many keys
                child_keys = self._parse_one2many_values(source_value)

                # Sync children với parent context
                self._sync_one2many_children(mapping.relation_model_id, child_keys, parent_record, mapping)

            except Exception as e:
                _logger.error("Lỗi xử lý one2many cache cho field %s: %s", field_name, str(e))

    def _sync_one2many_children(self, relation_mapping, child_keys, parent_record, field_mapping):
        """
        Sync one2many children với parent record
        """
        try:
            if not child_keys:
                return

            # Build WHERE clause cho child keys
            key_field = relation_mapping.source_key_field
            if len(child_keys) == 1:
                where_clause = f"{key_field} = '{child_keys[0]}'"
            else:
                escaped_keys = [str(k).replace("'", "''") for k in child_keys]
                values_str = "', '".join(escaped_keys)
                where_clause = f"{key_field} IN ('{values_str}')"

            # Tạo temp sync cho children
            temp_sync = self.env['psm.db.sync'].create({
                'name': f'One2many sync: {relation_mapping.name} → {parent_record._name}({parent_record.id})',
                'mapping_model_id': relation_mapping.id,
                'sync_type': 'full',
                'sync_action': 'create_update',
                'filter_where_clause': where_clause,
                'batch_size': 0,
                'use_queue': False,
                'execution_type': 'manual'
            })

            # Thực thi sync children
            sync_result = temp_sync._run_sync()
            if sync_result:
                _logger.info("Sync thành công %d one2many children cho %s",
                             len(child_keys), parent_record._name)
            else:
                _logger.warning("Sync one2many children thất bại")

            # Cleanup temp sync
            temp_sync.unlink()

        except Exception as e:
            _logger.error("Lỗi sync one2many children: %s", str(e))

    def _parse_one2many_values(self, source_value):
        """
        Parse one2many values từ comma-separated string
        """
        if not source_value:
            return []

        if isinstance(source_value, str):
            # Thử parse JSON trước
            try:
                import json
                parsed = json.loads(source_value)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    return [parsed]
            except:
                pass

            # Handle comma-separated keys: "123_1,123_2,123_3"
            if ',' in source_value:
                return [v.strip() for v in source_value.split(',') if v.strip()]
            else:
                return [source_value.strip()]

        elif isinstance(source_value, list):
            return source_value
        elif isinstance(source_value, dict):
            return [source_value]
        else:
            return [str(source_value)]
