# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VendorComplaint(models.Model):
    _name = 'vendor.complaint'
    _description = 'Vendor Complaint - Phiếu xử lý hàng thừa/thiếu/lỗi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Complaint Reference', required=True, copy=False, readonly=True, default='New')
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Vendor', related='picking_id.partner_id', store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse/Store', related='picking_id.picking_type_id.warehouse_id', store=True)
    
    # Link đến Backorder tự động tạo khi Store tạo Complaint
    backorder_id = fields.Many2one('stock.picking', string='Backorder (Phiếu chờ giao bù)', readonly=True,
                                   help="Phiếu backorder tự động tạo khi Store tạo Complaint. FSC sẽ quyết định Approve/Reject.")
    
    # Link đến Phiếu giao bù (Bước B10)
    compensation_picking_id = fields.Many2one('stock.picking', string='Phiếu Giao Bù', readonly=True, 
                                              help="Phiếu nhập kho hàng bù do NCC gửi lại")

    complaint_date = fields.Datetime('Complaint Date', default=fields.Datetime.now, required=True)
    
    complaint_type = fields.Selection([
        ('excess', 'Hàng thừa (TH1)'),
        ('shortage', 'Hàng thiếu (TH2)'),
        ('defect_province', 'Hàng lỗi - Tỉnh (TH3)'),
        ('defect_metro', 'Hàng lỗi - HCM/HN (TH4)'),
    ], string='Complaint Type', required=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('qa_review', 'QA Review - Bước 5'),    
        ('fsc_review', 'FSC Review - Bước 7'),
        ('approved', 'Approved - Chờ giao bù'),
        ('rejected', 'Rejected - Trả hàng'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    line_ids = fields.One2many('vendor.complaint.line', 'complaint_id', string='Complaint Lines')
    
    qa_notes = fields.Text('QA Notes')
    fsc_notes = fields.Text('FSC Notes')
    vendor_response = fields.Text('Vendor Response')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    
    # Link to Purchase Order (for invoice lookup)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', 
                                        related='picking_id.purchase_id', store=True)
    
    # Computed fields for Smart Buttons
    picking_count = fields.Integer('Transfer Count', compute='_compute_picking_count')
    invoice_count = fields.Integer('Invoice Count', compute='_compute_invoice_count')
    
    # Required attachment: Biên bản làm việc với NCC
    vendor_agreement_attachment = fields.Binary(
        'Biên bản làm việc với NCC',
        attachment=True,
        help="Bắt buộc upload trước khi FSC duyệt complaint"
    )
    vendor_agreement_filename = fields.Char('Attachment Filename')

    @api.depends('backorder_id', 'compensation_picking_id')
    def _compute_picking_count(self):
        for complaint in self:
            picking_ids = set()
            if complaint.backorder_id:
                picking_ids.add(complaint.backorder_id.id)
            if complaint.compensation_picking_id:
                picking_ids.add(complaint.compensation_picking_id.id)
            complaint.picking_count = len(picking_ids)

    @api.depends('purchase_order_id', 'purchase_order_id.invoice_ids')
    def _compute_invoice_count(self):
        for complaint in self:
            if complaint.purchase_order_id:
                complaint.invoice_count = len(complaint.purchase_order_id.invoice_ids)
            else:
                complaint.invoice_count = 0

    def action_view_transfers(self):
        """Open related backorder/compensation pickings"""
        self.ensure_one()
        # Collect all related picking IDs (avoid duplicates)
        picking_ids = set()
        if self.backorder_id:
            picking_ids.add(self.backorder_id.id)
        if self.compensation_picking_id:
            picking_ids.add(self.compensation_picking_id.id)
        
        result = {
            'name': _('Phiếu Giao Bù'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', list(picking_ids))],
            'context': {'create': False},
        }
        
        # If only 1 picking -> Open Form view directly
        if len(picking_ids) == 1:
            result['view_mode'] = 'form'
            result['res_id'] = list(picking_ids)[0]
        else:
            # Multiple pickings -> Open List view
            result['view_mode'] = 'list,form'
            
        return result

    def action_view_invoices(self):
        """Open vendor bills linked to original PO"""
        self.ensure_one()
        if not self.purchase_order_id:
            return True
            
        invoice_ids = self.purchase_order_id.invoice_ids.ids
        
        result = {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain': [('id', 'in', invoice_ids)],
            'context': {'create': False},
        }
        
        # If only 1 invoice -> Open Form view directly
        if len(invoice_ids) == 1:
            result['view_mode'] = 'form'
            result['res_id'] = invoice_ids[0]
        else:
            # Multiple invoices -> Open List view
            result['view_mode'] = 'list,form'
            
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vendor.complaint') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        """Submit complaint for review based on Complaint Type"""
        self.ensure_one()
        if self.complaint_type == 'excess':
            # TH1: Hàng thừa -> Nhận luôn (B2, B3)
            self.state = 'closed'
            self.message_post(body=_('TH1: Hàng thừa đã được chấp nhận và nhập kho.'))
            
        elif self.complaint_type == 'defect_metro':
            # TH4: Lỗi HCM/HN -> Không nhận (B4)
            self.state = 'closed'
            self.message_post(body=_('TH4: Hàng lỗi khu vực Metro - Đã từ chối nhận hàng.'))
            
        elif self.complaint_type == 'shortage':
            # TH2: Hàng thiếu -> Chuyển thẳng FSC (B7)
            self.state = 'fsc_review'
            self.message_post(body=_('TH2: Hàng thiếu - Chuyển FSC xem xét.'))
            
        elif self.complaint_type == 'defect_province':
            # TH3: Lỗi Tỉnh -> Chuyển QA xác định mức độ lỗi (B5)
            self.state = 'qa_review'
            self.message_post(body=_('TH3: Hàng lỗi Tỉnh - Chuyển QA xác định mức độ lỗi.'))
        return True

    def action_qa_propose(self):
        """QA Xác định mức độ lỗi và đề xuất phương án (B6)"""
        self.ensure_one()
        if not self.qa_notes:
            raise UserError(_("Vui lòng nhập ghi chú đánh giá của QA trước khi gửi FSC."))
        self.state = 'fsc_review'
        self.message_post(body=_('QA đã xác nhận lỗi. Chuyển FSC chốt phương án.'))
        return True

    def action_fsc_approve(self):
        """FSC Duyệt và gửi phiếu giao bù cho NCC (Bước 9)"""
        self.ensure_one()
        
        if self.backorder_id and self.backorder_id.state != 'cancel':
            # Set deadline: 48 hours from COMPLAINT CREATION (not approval time)
            from datetime import timedelta
            deadline = self.complaint_date + timedelta(hours=48)
            self.backorder_id.scheduled_date = deadline
            
            # Keep backorder and set as compensation picking
            self.compensation_picking_id = self.backorder_id.id
            self.state = 'approved'
            
            self.message_post(
                body=_('FSC đã duyệt. Phiếu giao bù: %s. Hạn giao: %s') % (
                    self.backorder_id.name, deadline
                )
            )
            
            # AUTO-SEND EMAIL TO VENDOR
            self._send_backorder_email_to_vendor()
            
            # Return action to view the backorder
            return {
                'name': _('Phiếu Giao Bù'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': self.backorder_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # No backorder (e.g., TH1 - excess items)
            self.state = 'approved'
            self.message_post(body=_('FSC đã duyệt - Không có phiếu giao bù.'))
            return True
    
    def _send_backorder_email_to_vendor(self):
        """Internal method: Send backorder email to vendor + post to chatter with PDF attachment"""
        backorder_name = self.backorder_id.name if self.backorder_id else "N/A"
        
        # Generate PDF report of backorder picking
        pdf_attachment = self._create_backorder_pdf_attachment()
        # Also generate barcode image
        barcode_attachment = self._create_barcode_attachment(backorder_name)
        
        # Collect attachments
        attachment_ids = []
        if pdf_attachment:
            attachment_ids.append(pdf_attachment.id)
        if barcode_attachment:
            attachment_ids.append(barcode_attachment.id)
        
        # 1. POST TO CHATTER with PDF attachment
        chatter_body = """
        <p><strong>📧 Thông báo phiếu giao bù đã được gửi đến NCC</strong></p>
        <ul>
            <li>NCC: %s</li>
            <li>Email: %s</li>
            <li>Phiếu giao bù: <strong>%s</strong></li>
            <li>Hạn giao: %s</li>
        </ul>
        <p><em>File đính kèm: Phiếu giao bù + Barcode để in dán lên đơn hàng.</em></p>
        """ % (
            self.partner_id.name,
            self.partner_id.email or "N/A",
            backorder_name,
            self.backorder_id.scheduled_date if self.backorder_id else "N/A"
        )
        
        self.message_post(
            body=chatter_body,
            attachment_ids=attachment_ids,
            message_type='notification'
        )
        
        # 2. SEND EMAIL (if email exists)
        if not self.partner_id.email:
            self.message_post(
                body=_('⚠️ Không thể gửi email: NCC %s chưa có địa chỉ email.') % self.partner_id.name
            )
            return False
        
        try:
            self.env['mail.mail'].create({
                'subject': _('Yêu cầu giao bù - %s - Phiếu %s') % (self.name, backorder_name),
                'email_to': self.partner_id.email,
                'body_html': self._get_backorder_email_body(),
                'attachment_ids': [(6, 0, attachment_ids)],  # Also attach barcode to email
            }).send()
            
            self.message_post(
                body=_('✅ Đã gửi email phiếu giao bù đến NCC: %s (%s)') % (
                    self.partner_id.name, self.partner_id.email
                )
            )
            return True
        except Exception as e:
            self.message_post(body=_('❌ Lỗi gửi email: %s') % str(e))
            return False
    
    def _create_backorder_pdf_attachment(self):
        """Create ir.attachment with PDF report of backorder picking"""
        if not self.backorder_id:
            return False
        
        import base64
        try:
            # Get the stock picking report
            report = self.env.ref('stock.action_report_delivery')
            
            # Generate PDF
            pdf_content, content_type = report._render_qweb_pdf(
                report.id, 
                [self.backorder_id.id]
            )
            
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': 'PhieuGiaoBu_%s.pdf' % self.backorder_id.name.replace('/', '_'),
                'type': 'binary',
                'datas': base64.b64encode(bytes(pdf_content)),  # type: ignore
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })
            return attachment
        except Exception as e:
            # Log error but don't fail the whole process
            self.message_post(body=_('⚠️ Không thể tạo PDF phiếu giao bù: %s') % str(e))
            return False
    
    def _create_barcode_attachment(self, barcode_value):
        """Create ir.attachment with barcode image"""
        import base64
        try:
            from odoo.tools import barcode  # type: ignore
            barcode_bytes = barcode.barcode('Code128', barcode_value, width=400, height=100, humanreadable=1)  # type: ignore
            
            attachment = self.env['ir.attachment'].create({
                'name': 'Barcode_%s.png' % barcode_value.replace('/', '_'),
                'type': 'binary',
                'datas': base64.b64encode(barcode_bytes),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'image/png',
            })
            return attachment
        except Exception as e:
            return False

    def action_fsc_reject(self):
        """FSC Chốt phương án: Không bù / Trả hàng (B8)"""
        self.ensure_one()
        
        # Cancel the backorder if it exists
        if self.backorder_id and self.backorder_id.state not in ['done', 'cancel']:
            self.backorder_id.action_cancel()
            self.message_post(body=_('FSC từ chối. Phiếu Backorder đã bị hủy.'))
        
        self.state = 'rejected'
        self.message_post(body=_('FSC từ chối nhận bù. Hàng sẽ được trả lại hoặc hủy PO.'))
        return True

    def action_close(self):
        """Hoàn tất quy trình"""
        self.ensure_one()
        self.state = 'closed'
        return True

    def action_send_to_vendor(self):
        """Gửi thông tin phiếu giao bù cho NCC qua email"""
        self.ensure_one()
        
        if not self.backorder_id:
            raise UserError(_("Không có phiếu giao bù để gửi cho NCC."))
        
        if not self.partner_id.email:
            raise UserError(_("NCC '%s' chưa có địa chỉ email. Vui lòng cập nhật trước.") % self.partner_id.name)
        
        # Try to use email template, fallback to simple message
        template = self.env.ref('psm_vendor_complaint.email_template_vendor_backorder', raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)
        else:
            # Fallback: Send simple email
            self.env['mail.mail'].create({
                'subject': _('Yêu cầu giao bù - %s') % self.name,
                'email_to': self.partner_id.email,
                'body_html': self._get_backorder_email_body(),
            }).send()
        
        self.message_post(body=_('Đã gửi thông tin phiếu giao bù đến NCC: %s (%s)') % (
            self.partner_id.name, self.partner_id.email
        ))
        
        return True
    
    def _get_backorder_email_body(self):
        """Generate email body for backorder notification with barcode"""
        lines_html = ""
        for line in self.line_ids:
            variance = line.ordered_qty - line.received_qty
            lines_html += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                line.product_id.display_name,
                line.ordered_qty,
                line.received_qty,
                variance
            )
        
        # Generate barcode as BASE64 inline image
        backorder_name = self.backorder_id.name if self.backorder_id else "N/A"
        
        # Use Odoo's barcode generation and encode to base64
        import base64
        try:
            from odoo.tools import barcode  # type: ignore
            # Generate Code128 barcode
            barcode_bytes = barcode.barcode('Code128', backorder_name, width=400, height=80, humanreadable=1)  # type: ignore
            barcode_base64 = base64.b64encode(barcode_bytes).decode('utf-8')
            barcode_img_tag = '<img src="data:image/png;base64,%s" alt="Barcode %s" style="max-width: 100%%;"/>' % (barcode_base64, backorder_name)
        except Exception as e:
            # Fallback: just show text if barcode generation fails
            barcode_img_tag = '<div style="font-family: monospace; font-size: 24px; letter-spacing: 3px;">||| %s |||</div>' % backorder_name
        
        
        return """
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #875A7B;">Yêu cầu giao hàng bù</h2>
            
            <p>Kính gửi <strong>%s</strong>,</p>
            <p>Chúng tôi thông báo về yêu cầu giao hàng bù:</p>
            
            <table cellpadding="5" style="margin-bottom: 15px;">
                <tr><td>Mã Complaint:</td><td><strong>%s</strong></td></tr>
                <tr><td>Phiếu nhập gốc:</td><td>%s</td></tr>
                <tr><td>Phiếu giao bù:</td><td><strong style="color: #875A7B; font-size: 18px;">%s</strong></td></tr>
                <tr><td>Hạn giao:</td><td><strong style="color: #D9534F;">%s</strong></td></tr>
            </table>
            
            <!-- BARCODE SECTION -->
            <div style="background: #f8f9fa; border: 2px dashed #875A7B; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #875A7B;">
                    📦 MÃ VẠCH PHIẾU GIAO BÙ - IN VÀ DÁN LÊN ĐƠN HÀNG
                </p>
                %s
                <p style="font-size: 20px; font-weight: bold; margin: 10px 0 0 0;">%s</p>
                <p style="font-size: 12px; color: #666; margin: 5px 0 0 0;">
                    Vui lòng in barcode này và dán lên đơn hàng giao bù để chúng tôi có thể quét mã khi nhận hàng.
                </p>
            </div>
            
            <p><strong>Chi tiết sản phẩm cần giao bù:</strong></p>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%%;">
                <tr style="background: #875A7B; color: white;">
                    <th>Sản phẩm</th><th>SL Đặt</th><th>SL Nhận</th><th>SL Thiếu</th>
                </tr>
                %s
            </table>
            
            <p style="margin-top: 20px;">Vui lòng giao hàng bù trước thời hạn trên.</p>
            <p>Trân trọng,<br/><strong>%s</strong></p>
        </div>
        """ % (
            self.partner_id.name,
            self.name,
            self.picking_id.name,
            backorder_name,
            self.backorder_id.scheduled_date if self.backorder_id else "N/A",
            barcode_img_tag,
            backorder_name,
            lines_html,
            self.company_id.name or "Công ty"
        )