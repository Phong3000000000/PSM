# -*- coding: utf-8 -*-

import json
import logging
from datetime import timedelta, datetime
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PsmDbSyncController(http.Controller):

    @http.route('/psm_db_sync/dashboard/data', type='jsonrpc', auth='user', methods=['POST'])
    def get_dashboard_data(self):
        """Lấy dữ liệu cho dashboard"""
        try:
            # Thống kê tổng quan
            connections = request.env['psm.db.connection'].search_count([('active', '=', True)])
            mappings = request.env['psm.db.mapping.model'].search_count([])
            sync_tasks = request.env['psm.db.sync'].search_count([('active', '=', True)])

            # Thống kê nhiệm vụ đồng bộ
            running_tasks = request.env['psm.db.sync'].search_count([('state', '=', 'running')])
            error_tasks = request.env['psm.db.sync'].search_count([('state', '=', 'error')])

            # Thống kê nhật ký gần đây
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_logs = request.env['psm.db.sync.log'].search([
                ('start_time', '>=', seven_days_ago)
            ], order='start_time desc', limit=10)

            logs_data = []
            for log in recent_logs:
                logs_data.append({
                    'id': log.id,
                    'sync_name': log.sync_id.name if log.sync_id else 'N/A',
                    'start_time': log.start_time.isoformat() if log.start_time else '',
                    'status': log.status,
                    'records_created': log.records_created,
                    'records_updated': log.records_updated,
                    'records_failed': log.records_failed,
                    'duration': log.duration,
                })

            # Thống kê kết nối
            connection_stats = []
            for conn in request.env['psm.db.connection'].search([('active', '=', True)]):
                try:
                    # Test kết nối
                    conn._get_engine()
                    status = 'connected'
                except:
                    status = 'error'

                connection_stats.append({
                    'id': conn.id,
                    'name': conn.name,
                    'db_type': conn.db_type,
                    'status': status,
                    'mapping_count': len(conn.mapping_model_ids),
                    'last_connection': conn.last_connection.isoformat() if conn.last_connection else None,
                })

            # Thống kê hiệu suất
            success_rate = 0
            if sync_tasks > 0:
                total_logs = request.env['psm.db.sync.log'].search_count([])
                success_logs = request.env['psm.db.sync.log'].search_count([('status', '=', 'completed')])
                success_rate = (success_logs / total_logs) * 100 if total_logs > 0 else 0

            return {
                'success': True,
                'data': {
                    'overview': {
                        'connections': connections,
                        'mappings': mappings,
                        'sync_tasks': sync_tasks,
                        'running_tasks': running_tasks,
                        'error_tasks': error_tasks,
                        'success_rate': round(success_rate, 2),
                    },
                    'recent_logs': logs_data,
                    'connections': connection_stats,
                }
            }

        except Exception as e:
            _logger.error("Lỗi lấy dữ liệu dashboard: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/psm_db_sync/connection/test', type='jsonrpc', auth='user', methods=['POST'])
    def test_connection(self, connection_id):
        """Test kết nối database"""
        try:
            connection = request.env['psm.db.connection'].browse(connection_id)

            if not connection.exists():
                return {
                    'success': False,
                    'error': _('Kết nối không tồn tại.')
                }

            # Test connection
            engine = connection._get_engine()
            conn = engine.connect()
            conn.close()

            # Cập nhật thống kê
            connection.write({
                'last_connection': datetime.now(),
                'connection_count': connection.connection_count + 1
            })

            return {
                'success': True,
                'message': _('Kết nối thành công!')
            }

        except Exception as e:
            _logger.error("Lỗi test kết nối %s: %s", connection_id, str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/psm_db_sync/sync/start', type='jsonrpc', auth='user', methods=['POST'])
    def start_sync(self, sync_id):
        """Bắt đầu đồng bộ"""
        try:
            sync_task = request.env['psm.db.sync'].browse(sync_id)

            if not sync_task.exists():
                return {
                    'success': False,
                    'error': _('Nhiệm vụ đồng bộ không tồn tại.')
                }

            if sync_task.state == 'running':
                return {
                    'success': False,
                    'error': _('Nhiệm vụ đồng bộ đang chạy.')
                }

            # Bắt đầu đồng bộ
            if sync_task.use_queue:
                sync_task.with_delay(description=f"Sync: {sync_task.name}").job_run_sync()
                message = _('Nhiệm vụ đã được đưa vào hàng đợi.')
            else:
                result = sync_task._run_sync()
                message = _('Đồng bộ hoàn thành.') if result else _('Đồng bộ thất bại.')

            return {
                'success': True,
                'message': message
            }

        except Exception as e:
            _logger.error("Lỗi bắt đầu đồng bộ %s: %s", sync_id, str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/psm_db_sync/tables/list', type='jsonrpc', auth='user', methods=['POST'])
    def get_table_list(self, connection_id):
        """Lấy danh sách bảng từ database"""
        try:
            connection = request.env['psm.db.connection'].browse(connection_id)

            if not connection.exists():
                return {
                    'success': False,
                    'error': _('Kết nối không tồn tại.')
                }

            tables = connection.get_table_list()

            return {
                'success': True,
                'data': tables
            }

        except Exception as e:
            _logger.error("Lỗi lấy danh sách bảng %s: %s", connection_id, str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/psm_db_sync/table/columns', type='jsonrpc', auth='user', methods=['POST'])
    def get_table_columns(self, connection_id, table_name):
        """Lấy thông tin cột của bảng"""
        try:
            connection = request.env['psm.db.connection'].browse(connection_id)

            if not connection.exists():
                return {
                    'success': False,
                    'error': _('Kết nối không tồn tại.')
                }

            columns = connection.get_table_columns(table_name)

            return {
                'success': True,
                'data': columns
            }

        except Exception as e:
            _logger.error("Lỗi lấy thông tin cột %s.%s: %s", connection_id, table_name, str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/psm_db_sync/query/execute', type='jsonrpc', auth='user', methods=['POST'])
    def execute_query(self, connection_id, query, limit=100):
        """Thực thi truy vấn SQL"""
        try:
            connection = request.env['psm.db.connection'].browse(connection_id)

            if not connection.exists():
                return {
                    'success': False,
                    'error': _('Kết nối không tồn tại.')
                }

            # Thêm LIMIT để bảo vệ
            if limit and limit > 0:
                if 'LIMIT' not in query.upper():
                    query = f"{query} LIMIT {limit}"

            result = connection.execute_query(query)

            return {
                'success': True,
                'data': result,
                'count': len(result)
            }

        except Exception as e:
            _logger.error("Lỗi thực thi truy vấn: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }