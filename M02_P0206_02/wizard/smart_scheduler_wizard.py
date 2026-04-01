# -*- coding: utf-8 -*-
import base64
import io
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SmartSchedulerWizard(models.TransientModel):
    """
    VLH Engine - Smart Scheduler Wizard
    Sinh lịch làm việc tự động từ dữ liệu SSBI (Sales History, Product Mix)
    """
    _name = 'smart.scheduler.wizard'
    _description = 'Wizard Sinh Lịch Thông Minh (VLH Engine)'

    # ===== INPUT FILES =====
    sales_history_file = fields.Binary(
        string='File Sales History (90 ngày)',
        help='File CSV/Excel chứa dữ liệu bán hàng 90 ngày gần nhất. Cột: Date, Hour, GC'
    )
    sales_history_filename = fields.Char(string='Tên file Sales')
    
    product_mix_file = fields.Binary(
        string='File Product Mix',
        help='File CSV/Excel chứa dữ liệu món ăn bán ra. Cột: Date, ItemCode, Qty'
    )
    product_mix_filename = fields.Char(string='Tên file Product Mix')
    
    # ===== CONFIG =====
    store_id = fields.Many2one(
        'hr.department',
        string='Cửa hàng',
        required=True
    )
    period_id = fields.Many2one(
        'planning.period',
        string='Kỳ đăng ký',
        required=True
    )
    target_date_from = fields.Date(
        string='Từ ngày',
        required=True
    )
    target_date_to = fields.Date(
        string='Đến ngày',
        required=True
    )
    trend_factor = fields.Float(
        string='Trend Factor',
        default=1.0,
        help='Hệ số điều chỉnh. VD: 1.05 = dự báo tăng 5%'
    )
    
    # ===== SHIFT CONFIG =====
    shift_template_ids = fields.Many2many(
        'workforce.shift.template',
        string='Mẫu ca làm việc',
        required=True,
        domain="[('is_active', '=', True)]"
    )
    
    # ===== OPTIONS =====
    use_forecast = fields.Boolean(
        string='Sử dụng VLH Forecast',
        default=True,
        help='Nếu bật, hệ thống sẽ tính số slot dựa trên dữ liệu từ file SSBI'
    )
    generate_per_station = fields.Boolean(
        string='Sinh theo từng Trạm',
        default=True,
        help='Tạo slot riêng biệt cho từng trạm làm việc'
    )
    
    # ===== DEFAULT ROLE (fallback) =====
    default_role_id = fields.Many2one(
        'planning.role',
        string='Vai trò mặc định'
    )
    
    @api.onchange('period_id')
    def _onchange_period_id(self):
        if self.period_id:
            self.target_date_from = self.period_id.date_from
            self.target_date_to = self.period_id.date_to
    
    @api.constrains('target_date_from', 'target_date_to')
    def _check_dates(self):
        for rec in self:
            if rec.target_date_from and rec.target_date_to:
                if rec.target_date_from > rec.target_date_to:
                    raise ValidationError(_('Ngày bắt đầu phải trước ngày kết thúc!'))
    
    def action_import_and_generate(self):
        """
        Main process: Import SSBI files → Calculate ProGC → Calculate UPT → Generate Slots
        """
        self.ensure_one()
        
        if not self.period_id:
            raise UserError(_('Vui lòng chọn Kỳ đăng ký!'))
        
        if self.period_id.state not in ['draft', 'open']:
            raise UserError(_('Chỉ có thể sinh lịch cho kỳ đang ở trạng thái Nháp hoặc Đang mở!'))
        
        if not self.shift_template_ids:
            raise UserError(_('Vui lòng chọn ít nhất một Mẫu ca làm việc!'))
        
        # Step 1: Parse Sales History and calculate ProGC
        pro_gc = {}
        if self.use_forecast and self.sales_history_file:
            gc_data = self._parse_sales_history()
            pro_gc = self._calculate_pro_gc(gc_data)
        
        # Step 2: Parse Product Mix and calculate UPT Ratios (optional)
        if self.product_mix_file:
            self._calculate_upt_ratios()
        
        # Step 3: Generate Slots
        if self.generate_per_station:
            slots_created = self._generate_slots_per_station(pro_gc)
        else:
            slots_created = self._generate_slots_simple(pro_gc)
        
        # Post message to Period
        self.period_id.message_post(
            body=_('VLH Engine: Đã sinh %s ca làm việc từ %s đến %s.') % (
                slots_created,
                self.target_date_from.strftime('%d/%m/%Y'),
                self.target_date_to.strftime('%d/%m/%Y')
            ),
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ca làm việc đã tạo'),
            'res_model': 'planning.slot',
            'view_mode': 'list,gantt',
            'domain': [('period_id', '=', self.period_id.id)],
            'context': {'default_period_id': self.period_id.id},
        }
    
    def _parse_sales_history(self):
        """
        Parse Sales History CSV file
        Expected columns: Date, Hour, GC
        Returns: list of {'date': date, 'weekday': int, 'hour': int, 'gc': float}
        """
        if not self.sales_history_file:
            return []
        
        try:
            file_content = base64.b64decode(self.sales_history_file)
            file_io = io.StringIO(file_content.decode('utf-8'))
            reader = csv.DictReader(file_io)
            
            gc_data = []
            for row in reader:
                # Handle different date formats
                date_str = row.get('Date') or row.get('date') or row.get('DATE')
                hour_str = row.get('Hour') or row.get('hour') or row.get('HOUR')
                gc_str = row.get('GC') or row.get('gc') or row.get('Guest Count') or row.get('guest_count')
                
                if not date_str or not hour_str or not gc_str:
                    continue
                
                # Parse date
                try:
                    date_obj = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
                    except ValueError:
                        continue
                
                # Parse hour and gc
                try:
                    hour = int(float(hour_str.strip()))
                    gc = float(gc_str.strip())
                except (ValueError, TypeError):
                    continue
                
                gc_data.append({
                    'date': date_obj,
                    'weekday': date_obj.weekday(),  # 0=Monday, 6=Sunday
                    'hour': hour,
                    'gc': gc,
                })
            
            return gc_data
            
        except Exception as e:
            raise UserError(_('Lỗi đọc file Sales History: %s') % str(e))
    
    def _calculate_pro_gc(self, gc_data):
        """
        Calculate ProGC (Forecast Guest Count)
        Formula: ProGC[h,d] = Average(GC[h,d]) in last 90 days × Trend Factor
        
        Args:
            gc_data: list of {'weekday': int, 'hour': int, 'gc': float}
        Returns:
            dict: {(weekday, hour): avg_gc}
        """
        if not gc_data:
            return {}
        
        # Group by (weekday, hour)
        grouped = defaultdict(list)
        for row in gc_data:
            key = (row['weekday'], row['hour'])
            grouped[key].append(row['gc'])
        
        # Calculate weighted average with trend factor
        pro_gc = {}
        for key, gc_list in grouped.items():
            avg_gc = sum(gc_list) / len(gc_list) if gc_list else 0
            pro_gc[key] = avg_gc * self.trend_factor
        
        return pro_gc
    
    def _calculate_upt_ratios(self):
        """
        Calculate UPT Ratio for each Station from Product Mix
        Formula: UPT Ratio = Total Station Qty / Total GC
        Updates: workforce.station.current_upt_ratio
        """
        if not self.product_mix_file:
            return
        
        try:
            file_content = base64.b64decode(self.product_mix_file)
            file_io = io.StringIO(file_content.decode('utf-8'))
            reader = csv.DictReader(file_io)
            
            # Group quantities by item code
            item_quantities = defaultdict(float)
            total_qty = 0
            
            for row in reader:
                item_code = row.get('ItemCode') or row.get('item_code') or row.get('ITEMCODE')
                qty_str = row.get('Qty') or row.get('qty') or row.get('QTY') or row.get('Quantity')
                
                if not item_code or not qty_str:
                    continue
                
                try:
                    qty = float(qty_str.strip())
                except (ValueError, TypeError):
                    continue
                
                item_quantities[item_code.strip()] = item_quantities[item_code.strip()] + qty
                total_qty += qty
            
            if total_qty == 0:
                return
            
            # Map items to stations and calculate ratios
            Station = self.env['workforce.station']
            ProductTemplate = self.env['product.template']
            
            station_quantities = defaultdict(float)
            
            for item_code, qty in item_quantities.items():
                # Find product by default_code
                products = ProductTemplate.search([('default_code', '=', item_code)], limit=1)
                if products and hasattr(products, 'workforce_station_ids'):
                    for station in products.workforce_station_ids:
                        station_quantities[station.id] += qty
            
            # Update station UPT ratios
            for station_id, station_qty in station_quantities.items():
                station = Station.browse(station_id)
                if station.exists():
                    station.current_upt_ratio = station_qty / total_qty
                    
        except Exception as e:
            # Log but don't fail - UPT calculation is optional
            pass
    
    def _generate_slots_per_station(self, pro_gc):
        """
        Generate slots per hour per station based on positioning guide
        """
        PlanningSlot = self.env['planning.slot']
        Station = self.env['workforce.station']
        PositioningGuide = self.env['workforce.positioning.guide']
        
        stations = Station.search([('active', '=', True)])
        if not stations:
            return self._generate_slots_simple(pro_gc)
        
        slots_created = 0
        current_date = self.target_date_from
        sorted_templates = self.shift_template_ids.sorted('sequence')
        
        while current_date <= self.target_date_to:
            weekday = current_date.weekday()
            
            for template in sorted_templates:
                # Get average GC for this shift time
                start_hour = int(template.start_hour)
                end_hour = int(template.end_hour) if template.end_hour > template.start_hour else int(template.end_hour) + 24
                
                # Calculate average GC across the shift hours
                shift_gc = 0
                hour_count = 0
                for h in range(start_hour, min(end_hour, 24)):
                    key = (weekday, h)
                    if key in pro_gc:
                        shift_gc += pro_gc[key]
                        hour_count += 1
                
                avg_gc = shift_gc / hour_count if hour_count > 0 else 10  # Default GC
                
                # Calculate slots for each station
                for station in stations:
                    # Calculate workload for this station
                    upt_ratio = station.current_upt_ratio if station.current_upt_ratio > 0 else 0.2
                    workload = avg_gc * upt_ratio
                    
                    # Lookup positioning guide
                    headcount = PositioningGuide.get_required_headcount(station.id, workload)
                    
                    if headcount <= 0:
                        continue
                    
                    # Get role for this station
                    role_id = station.planning_role_id.id if station.planning_role_id else (
                        self.default_role_id.id if self.default_role_id else False
                    )
                    
                    # Create datetime (local time → UTC will be handled by Odoo)
                    start_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=template.start_hour)
                    if template.end_hour < template.start_hour:
                        end_dt = datetime.combine(current_date + timedelta(days=1), datetime.min.time()) + timedelta(hours=template.end_hour)
                    else:
                        end_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=template.end_hour)
                    
                    # Create slots
                    for i in range(headcount):
                        PlanningSlot.create({
                            'start_datetime': start_dt,
                            'end_datetime': end_dt,
                            'period_id': self.period_id.id,
                            'store_id': self.store_id.id,
                            'role_id': role_id,
                            'state': 'draft',
                            'approval_state': 'open',
                            'allocated_hours': (end_dt - start_dt).total_seconds() / 3600.0,
                        })
                        slots_created += 1
            
            current_date += timedelta(days=1)
        
        return slots_created
    
    def _generate_slots_simple(self, pro_gc):
        """
        Simple slot generation without station breakdown
        Fallback method if no stations are configured
        """
        PlanningSlot = self.env['planning.slot']
        
        slots_created = 0
        current_date = self.target_date_from
        sorted_templates = self.shift_template_ids.sorted('sequence')
        
        min_headcount = 2
        max_headcount = 8
        
        while current_date <= self.target_date_to:
            weekday = current_date.weekday()
            
            for template in sorted_templates:
                # Get average GC for this shift
                start_hour = int(template.start_hour)
                shift_gc = 0
                hour_count = 0
                
                end_hour_calc = int(template.end_hour) if template.end_hour > template.start_hour else int(template.end_hour) + 24
                for h in range(start_hour, min(end_hour_calc, 24)):
                    key = (weekday, h)
                    if key in pro_gc:
                        shift_gc += pro_gc[key]
                        hour_count += 1
                
                avg_gc = shift_gc / hour_count if hour_count > 0 else 20
                
                # Simple headcount calculation: 1 person per 10 GC
                headcount = max(min_headcount, min(int(avg_gc / 10) + 1, max_headcount))
                
                # Peak adjustment
                if hasattr(template, 'is_peak') and template.is_peak:
                    headcount = min(headcount + 2, max_headcount)
                
                # Create datetime
                start_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=template.start_hour)
                if template.end_hour < template.start_hour:
                    end_dt = datetime.combine(current_date + timedelta(days=1), datetime.min.time()) + timedelta(hours=template.end_hour)
                else:
                    end_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=template.end_hour)
                
                # Create slots
                for i in range(headcount):
                    PlanningSlot.create({
                        'start_datetime': start_dt,
                        'end_datetime': end_dt,
                        'period_id': self.period_id.id,
                        'store_id': self.store_id.id,
                        'role_id': self.default_role_id.id if self.default_role_id else False,
                        'state': 'draft',
                        'approval_state': 'open',
                        'allocated_hours': (end_dt - start_dt).total_seconds() / 3600.0,
                    })
                    slots_created += 1
            
            current_date += timedelta(days=1)
        
        return slots_created
    
    # Keep old method for backward compatibility
    def action_generate(self):
        """Legacy method - redirects to new implementation"""
        return self.action_import_and_generate()


