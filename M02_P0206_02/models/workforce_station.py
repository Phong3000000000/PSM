# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WorkforceStation(models.Model):
    """
    Trạm làm việc (Station)
    Mapping các trạm và năng suất chuẩn
    VD: RINI (Runner In), FCOT (FC Out), DTOT (Drive-thru Out)
    """
    _name = 'workforce.station'
    _description = 'Trạm Làm Việc'
    _order = 'sequence, code'

    code = fields.Char(
        string='Mã trạm',
        required=True,
        index=True,
        help='Mã ngắn gọn của trạm. VD: RINI, FCOT, DTOT'
    )
    name = fields.Char(
        string='Tên trạm',
        required=True,
        help='Tên đầy đủ của trạm. VD: Runner In, FC Out, Drive-thru Out'
    )
    sequence = fields.Integer(
        string='Thứ tự',
        default=10
    )
    active = fields.Boolean(
        default=True
    )
    
    # Mapping to Planning Role for display color
    planning_role_id = fields.Many2one(
        'planning.role',
        string='Role hiển thị',
        help='Liên kết với Planning Role để hiển thị màu sắc trên lịch'
    )
    
    # Productivity Standard
    productivity_standard = fields.Float(
        string='Năng suất chuẩn',
        default=50.0,
        help='Số Items/Hour mà một nhân viên tại trạm này có thể xử lý'
    )
    
    # Current UPT Ratio - Computed from Product Mix import
    current_upt_ratio = fields.Float(
        string='Tỷ trọng UPT',
        default=0.0,
        help='Tỷ trọng UPT (Unit Per Transaction) của trạm này. Được tính tự động từ file Product Mix'
    )
    
    # Positioning Guide lines
    positioning_guide_ids = fields.One2many(
        'workforce.positioning.guide',
        'station_id',
        string='Bảng định biên'
    )
    
    # Description/Notes
    description = fields.Text(
        string='Mô tả'
    )
    
    _sql_constraints = [
        (
            'code_unique',
            'UNIQUE(code)',
            'Mã trạm đã tồn tại!'
        ),
    ]
    
    def name_get(self):
        result = []
        for rec in self:
            name = '[%s] %s' % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)


class WorkforcePositioningGuide(models.Model):
    """
    Bảng tra định biên nhân sự (Positioning Guide)
    Logic: Với lượng khách (GC) nằm trong khoảng A -> B thì cần N nhân viên
    """
    _name = 'workforce.positioning.guide'
    _description = 'Bảng Định Biên Nhân Sự'
    _order = 'station_id, min_gc'

    station_id = fields.Many2one(
        'workforce.station',
        string='Trạm',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    min_gc = fields.Integer(
        string='GC tối thiểu',
        required=True,
        default=0,
        help='Số lượng khách tối thiểu để áp dụng định biên này'
    )
    max_gc = fields.Integer(
        string='GC tối đa',
        required=True,
        default=50,
        help='Số lượng khách tối đa để áp dụng định biên này'
    )
    required_headcount = fields.Integer(
        string='Số nhân sự cần',
        required=True,
        default=1,
        help='Số lượng Slot cần tạo cho khoảng GC này'
    )
    
    @api.constrains('min_gc', 'max_gc')
    def _check_gc_range(self):
        for rec in self:
            if rec.min_gc < 0:
                raise ValidationError(_('GC tối thiểu không được âm!'))
            if rec.max_gc < rec.min_gc:
                raise ValidationError(_('GC tối đa phải lớn hơn hoặc bằng GC tối thiểu!'))
    
    @api.constrains('required_headcount')
    def _check_headcount(self):
        for rec in self:
            if rec.required_headcount < 0:
                raise ValidationError(_('Số nhân sự cần không được âm!'))
    
    @api.model
    def get_required_headcount(self, station_id, workload):
        """
        Tra bảng định biên để lấy số nhân sự cần
        Args:
            station_id: ID của workforce.station
            workload: Khối lượng công việc (GC × UPT Ratio)
        Returns:
            required_headcount hoặc 1 nếu không tìm thấy
        """
        guide = self.search([
            ('station_id', '=', station_id),
            ('min_gc', '<=', workload),
            ('max_gc', '>=', workload),
        ], limit=1)
        
        if guide:
            return guide.required_headcount
        
        # Nếu workload vượt max, lấy dòng có max_gc lớn nhất
        guide = self.search([
            ('station_id', '=', station_id),
        ], order='max_gc desc', limit=1)
        
        return guide.required_headcount if guide else 1
