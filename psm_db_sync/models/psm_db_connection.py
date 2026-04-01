# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import sqlalchemy
from sqlalchemy import create_engine, inspect, MetaData
import json
from urllib.parse import quote_plus

_logger = logging.getLogger(__name__)

DB_ENGINE_TYPES = [
    ('mysql', 'MySQL'),
    ('postgresql', 'PostgreSQL'),
    ('mssql', 'MS SQL Server'),
    ('oracle', 'Oracle'),
    ('mariadb', 'MariaDB'),
]

# MSSQL Connection Types
MSSQL_CONNECTION_TYPES = [
    ('pyodbc', 'ODBC Driver (pyodbc)'),
    ('pymssql', 'Native Driver (pymssql)'),
]

# Available ODBC Drivers for MSSQL
MSSQL_ODBC_DRIVERS = [
    ('ODBC Driver 18 for SQL Server', 'ODBC Driver 18 for SQL Server'),
    ('ODBC Driver 17 for SQL Server', 'ODBC Driver 17 for SQL Server'),
    ('ODBC Driver 13 for SQL Server', 'ODBC Driver 13 for SQL Server'),
    ('ODBC Driver 11 for SQL Server', 'ODBC Driver 11 for SQL Server'),
    ('SQL Server Native Client 11.0', 'SQL Server Native Client 11.0'),
    ('SQL Server', 'SQL Server (Legacy)'),
]

ALLOWED_SQL_KEYWORDS = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'ORDER BY', 'GROUP BY', 'LIMIT']


class PsmDbConnection(models.Model):
    _name = 'psm.db.connection'
    _description = 'Database Connection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Tên kết nối', required=True, tracking=True, index=True)
    db_type = fields.Selection(DB_ENGINE_TYPES, string='Loại CSDL', required=True, tracking=True)
    host = fields.Char(string='Host', required=True, tracking=True, help="Địa chỉ máy chủ cơ sở dữ liệu")
    port = fields.Integer(string='Port', required=True, tracking=True)
    database = fields.Char(string='Tên CSDL', required=True, tracking=True)
    username = fields.Char(string='Tên đăng nhập', required=True, tracking=True)
    password = fields.Char(string='Mật khẩu', required=True)

    # MSSQL specific fields
    mssql_connection_type = fields.Selection(
        MSSQL_CONNECTION_TYPES,
        string='Kiểu kết nối MSSQL',
        default='pyodbc',
        help="Chọn kiểu driver để kết nối MSSQL"
    )
    mssql_odbc_driver = fields.Selection(
        MSSQL_ODBC_DRIVERS,
        string='ODBC Driver',
        default='ODBC Driver 18 for SQL Server',
        help="Chọn ODBC driver cụ thể cho MSSQL"
    )
    mssql_trust_certificate = fields.Boolean(
        string='Trust Server Certificate',
        default=True,
        help="Tin tưởng chứng chỉ máy chủ (TrustServerCertificate=yes)"
    )
    mssql_encrypt_connection = fields.Boolean(
        string='Encrypt Connection',
        default=True,
        help="Mã hóa kết nối (Encrypt=yes)"
    )
    mssql_instance = fields.Char(
        string='Instance Name',
        help="Tên instance SQL Server (để trống nếu dùng default instance)"
    )

    # SSL Options
    use_ssl = fields.Boolean(string='Sử dụng SSL', default=False, tracking=True)
    ssl_ca = fields.Binary(string='CA Certificate', attachment=True, tracking=True)
    ssl_cert = fields.Binary(string='Client Certificate', attachment=True, tracking=True)
    ssl_key = fields.Binary(string='Client Key', attachment=True, tracking=True)

    # Extended Options
    connection_timeout = fields.Integer(string='Thời gian chờ kết nối (giây)', default=60, tracking=True)
    additional_params = fields.Text(string='Tham số bổ sung',
                                    help="Các tham số kết nối bổ sung dưới dạng JSON")

    # Status and statistics
    active = fields.Boolean(string='Đang hoạt động', default=True, tracking=True)
    last_connection = fields.Datetime(string='Kết nối gần nhất', tracking=True)
    connection_count = fields.Integer(string='Số lần kết nối', default=0)

    # Relations
    mapping_model_ids = fields.One2many('psm.db.mapping.model', 'connection_id', string='Ánh xạ mô hình')
    mapping_model_count = fields.Integer(compute='_compute_mapping_model_count', string='Số lượng ánh xạ')

    company_id = fields.Many2one('res.company', string='Công ty',
                                 required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Người phụ trách',
                              default=lambda self: self.env.user, tracking=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Set default port based on db_type
        if 'db_type' in res and 'port' not in res:
            if res['db_type'] == 'mysql' or res['db_type'] == 'mariadb':
                res['port'] = 3306
            elif res['db_type'] == 'postgresql':
                res['port'] = 5432
            elif res['db_type'] == 'mssql':
                res['port'] = 1433
            elif res['db_type'] == 'oracle':
                res['port'] = 1521
        return res

    @api.depends('mapping_model_ids')
    def _compute_mapping_model_count(self):
        for record in self:
            record.mapping_model_count = len(record.mapping_model_ids)

    @api.onchange('db_type')
    def _onchange_db_type(self):
        if self.db_type == 'mysql' or self.db_type == 'mariadb':
            self.port = 3306
        elif self.db_type == 'postgresql':
            self.port = 5432
        elif self.db_type == 'mssql':
            self.port = 1433
        elif self.db_type == 'oracle':
            self.port = 1521

    def action_test_connection(self):
        self.ensure_one()
        try:
            engine = self._get_engine()
            connection = engine.connect()
            connection.close()
            self.write({
                'last_connection': fields.Datetime.now(),
                'connection_count': self.connection_count + 1
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Kết nối tới %s thành công!') % self.name,
                    'sticky': False,
                    'type': 'success'
                }
            }
        except Exception as e:
            raise UserError(_('Không thể kết nối tới cơ sở dữ liệu.\nLỗi: %s') % str(e))

    def _get_engine(self):
        self.ensure_one()

        connection_url = None
        ssl_args = {}

        # Parse additional_params if provided
        additional_params = {}
        if self.additional_params:
            try:
                additional_params = json.loads(self.additional_params)
            except Exception as e:
                _logger.warning("Could not parse additional_params: %s", str(e))

        # Handle SSL options (for MySQL/PostgreSQL)
        if self.use_ssl and self.db_type in ('mysql', 'mariadb', 'postgresql'):
            import tempfile
            import base64
            import os

            temp_dir = tempfile.mkdtemp()

            if self.ssl_ca:
                ca_path = os.path.join(temp_dir, 'ca.pem')
                with open(ca_path, 'wb') as f:
                    f.write(base64.b64decode(self.ssl_ca))
                ssl_args['ssl_ca'] = ca_path

            if self.ssl_cert:
                cert_path = os.path.join(temp_dir, 'cert.pem')
                with open(cert_path, 'wb') as f:
                    f.write(base64.b64decode(self.ssl_cert))
                ssl_args['ssl_cert'] = cert_path

            if self.ssl_key:
                key_path = os.path.join(temp_dir, 'key.pem')
                with open(key_path, 'wb') as f:
                    f.write(base64.b64decode(self.ssl_key))
                ssl_args['ssl_key'] = key_path

        # Build connection URL based on the database type
        if self.db_type == 'mysql' or self.db_type == 'mariadb':
            connection_url = f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            engine = create_engine(connection_url, connect_args=ssl_args, **additional_params)

        elif self.db_type == 'postgresql':
            connection_url = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            engine = create_engine(connection_url, **additional_params)

        elif self.db_type == 'mssql':
            engine = self._create_mssql_engine(additional_params)

        elif self.db_type == 'oracle':
            try:
                import cx_Oracle
                dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.database)
                connection_url = f"oracle://{self.username}:{self.password}@{dsn}"
                engine = create_engine(connection_url, **additional_params)
            except ImportError:
                raise UserError(_('Thư viện cx_Oracle chưa được cài đặt. Vui lòng cài đặt: pip install cx_Oracle'))

        return engine

    def _create_mssql_engine(self, additional_params):
        """Tạo MSSQL engine với các tùy chọn driver khác nhau"""

        if self.mssql_connection_type == 'pymssql':
            return self._create_pymssql_engine(additional_params)
        else:  # pyodbc
            return self._create_pyodbc_mssql_engine(additional_params)

    def _create_pymssql_engine(self, additional_params):
        """Tạo kết nối MSSQL sử dụng pymssql driver"""
        try:
            import pymssql
        except ImportError:
            raise UserError(_('Thư viện pymssql chưa được cài đặt. Vui lòng cài đặt: pip install pymssql'))

        # Xây dựng server string
        server = self.host
        if self.mssql_instance:
            server = f"{self.host}\\{self.mssql_instance}"
        elif self.port and self.port != 1433:
            server = f"{self.host}:{self.port}"

        connection_url = f"mssql+pymssql://{self.username}:{quote_plus(self.password)}@{server}/{self.database}"

        # Tùy chọn connect_args cho pymssql
        connect_args = {
            'timeout': self.connection_timeout,
            'login_timeout': self.connection_timeout,
            'tds_version': '7.0',
            'autocommit': True,
        }

        # Thêm charset nếu cần
        if 'charset' not in additional_params:
            connect_args['charset'] = 'utf8'

        _logger.info("Creating pymssql connection: %s", connection_url.replace(self.password, '***'))

        return create_engine(
            connection_url,
            connect_args=connect_args,
            **additional_params
        )

    def _create_pyodbc_mssql_engine(self, additional_params):
        """Tạo kết nối MSSQL sử dụng pyodbc driver"""
        try:
            import pyodbc
        except ImportError:
            raise UserError(_('Thư viện pyodbc chưa được cài đặt. Vui lòng cài đặt: pip install pyodbc'))

        # Kiểm tra driver có sẵn
        available_drivers = pyodbc.drivers()
        if self.mssql_odbc_driver not in available_drivers:
            _logger.warning("Driver '%s' không có sẵn. Available drivers: %s",
                            self.mssql_odbc_driver, available_drivers)
            # Tự động chọn driver có sẵn
            for driver in [d[0] for d in MSSQL_ODBC_DRIVERS]:
                if driver in available_drivers:
                    self.mssql_odbc_driver = driver
                    _logger.info("Automatically selected available driver: %s", driver)
                    break
            else:
                raise UserError(_(
                    'Không tìm thấy ODBC driver phù hợp.\n'
                    'Drivers có sẵn: %s\n'
                    'Vui lòng cài đặt ODBC driver hoặc chọn driver khác.'
                ) % ', '.join(available_drivers))

        # Xây dựng server string
        server = self.host
        if self.mssql_instance:
            server = f"{self.host}\\{self.mssql_instance}"
        elif self.port and self.port != 1433:
            server = f"{self.host},{self.port}"

        # Xây dựng ODBC connection string
        odbc_params = [
            f"DRIVER={{{self.mssql_odbc_driver}}}",
            f"SERVER={server}",
            f"DATABASE={self.database}",
            f"UID={self.username}",
            f"PWD={self.password}",
        ]

        # Thêm các tùy chọn bảo mật
        if self.mssql_trust_certificate:
            odbc_params.append("TrustServerCertificate=yes")

        if self.mssql_encrypt_connection:
            odbc_params.append("Encrypt=yes")
        else:
            odbc_params.append("Encrypt=no")

        # Thêm timeout
        if self.connection_timeout:
            odbc_params.append(f"Connection Timeout={self.connection_timeout}")

        # Thêm các tham số từ additional_params vào ODBC string
        if self.additional_params:
            try:
                extra_params = json.loads(self.additional_params)
                for key, value in extra_params.items():
                    if key.lower() not in ['driver', 'server', 'database', 'uid', 'pwd']:
                        odbc_params.append(f"{key}={value}")
            except Exception as e:
                _logger.warning("Error parsing additional_params for ODBC: %s", str(e))

        odbc_str = ';'.join(odbc_params)
        connection_url = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"

        _logger.info("Creating ODBC connection with driver: %s", self.mssql_odbc_driver)
        _logger.debug("ODBC connection string: %s", odbc_str.replace(self.password, '***'))

        return create_engine(
            connection_url,
            **{k: v for k, v in additional_params.items() if k not in ['charset', 'timeout']}
        )

    def action_test_drivers(self):
        """Kiểm tra các driver có sẵn trên hệ thống"""
        self.ensure_one()

        if self.db_type != 'mssql':
            raise UserError(_('Chức năng này chỉ dành cho MSSQL'))

        try:
            import pyodbc
            available_drivers = pyodbc.drivers()

            message = _('ODBC Drivers có sẵn:\n') + '\n'.join([f"• {driver}" for driver in available_drivers])

            # Kiểm tra pymssql
            try:
                import pymssql
                message += _('\n\n✅ pymssql driver: Có sẵn')
            except ImportError:
                message += _('\n\n❌ pymssql driver: Không có sẵn')

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thông tin Driver'),
                    'message': message,
                    'sticky': True,
                    'type': 'info'
                }
            }
        except ImportError:
            raise UserError(_('pyodbc chưa được cài đặt. Vui lòng cài đặt: pip install pyodbc'))

    def get_table_list(self):
        """Get list of tables from the external database"""
        self.ensure_one()

        engine = self._get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        return tables

    def get_table_columns(self, table_name):
        """Get columns information for a specific table"""
        self.ensure_one()

        engine = self._get_engine()
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)

        return columns

    def _validate_query(self, query):
        query_upper = query.upper().strip()
        if not query_upper.startswith('SELECT') and not query_upper.startswith('WITH RECURSIVE'):
            raise UserError(_('Chỉ cho phép câu lệnh SELECT or WITH RECURSIVE'))

        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise UserError(_('Câu lệnh không được phép chứa: %s') % keyword)

    def execute_query(self, query, params=None):
        """Execute a custom query on the external database"""
        self.ensure_one()

        engine = self._get_engine()
        connection = engine.connect()
        self._validate_query(query)

        try:
            if params:
                result = connection.execute(sqlalchemy.text(query), params)
            else:
                result = connection.execute(sqlalchemy.text(query))

            # Sử dụng mappings() để lấy dictionary thay vì dict(row)
            data = [dict(row._mapping) for row in result]
            connection.close()
            return data
        except Exception as e:
            connection.close()
            raise UserError(_('Lỗi thực thi truy vấn: %s') % str(e))

    def action_view_mappings(self):
        self.ensure_one()
        return {
            'name': _('Ánh xạ mô hình'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.mapping.model',
            'view_mode': 'tree,form',
            'domain': [('connection_id', '=', self.id)],
            'context': {'default_connection_id': self.id},
        }

    def action_get_metadata(self):
        """Lấy metadata từ cơ sở dữ liệu và hiển thị thông tin"""
        self.ensure_one()

        try:
            engine = self._get_engine()
            metadata = MetaData()
            metadata.reflect(bind=engine)

            tables_info = []
            for table in metadata.sorted_tables:
                columns = []
                primary_keys = []
                foreign_keys = []

                # Get columns
                for c in table.columns:
                    col_info = {
                        'name': c.name,
                        'type': str(c.type),
                        'nullable': c.nullable,
                    }
                    columns.append(col_info)

                # Get primary keys
                for pk in table.primary_key.columns:
                    primary_keys.append(pk.name)

                # Get foreign keys
                for fk in table.foreign_keys:
                    fk_info = {
                        'column': fk.parent.name,
                        'references_table': fk.column.table.name,
                        'references_column': fk.column.name
                    }
                    foreign_keys.append(fk_info)

                tables_info.append({
                    'name': table.name,
                    'columns': columns,
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys
                })

            # Return the result in a view
            view_id = self.env.ref('psm_db_sync.view_psm_db_metadata_wizard_form').id
            return {
                'name': _('Thông tin metadata'),
                'type': 'ir.actions.act_window',
                'res_model': 'psm.db.metadata.wizard',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'context': {'default_connection_id': self.id, 'default_metadata': json.dumps(tables_info)},
            }

        except Exception as e:
            raise UserError(_('Không thể lấy metadata: %s') % str(e))
