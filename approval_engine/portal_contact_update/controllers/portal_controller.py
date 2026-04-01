from odoo import http
from odoo.http import request
import base64

class PortalContactController(http.Controller):
    
    @http.route('/my/contact', type='http', auth='user', website=True)
    def portal_contact_page(self, **post):
        """Main portal page for contact to update personal documents"""
        partner = request.env.user.partner_id
        
        # Get document completion status
        doc_status = partner.get_portal_documents_status()
        
        return request.render('portal_contact_update.portal_contact_form', {
            'partner': partner,
            'doc_status': doc_status,
            'success': post.get('success', False)
        })
    
    @http.route('/my/contact/update', type='http', auth='user', website=True, csrf=True, methods=['POST'])
    def update_contact_info(self, **post):
        """Handle form submission from portal"""
        partner = request.env.user.partner_id
        
        try:
            update_vals = {}
            
            # List of document fields
            document_fields = [
                'passport_photo',
                'id_card_front',
                'id_card_back',
                'household_registration',
                'judicial_record',
                'professional_certificate',
                'additional_certificates'
            ]
            
            # Handle file uploads for each document
            for field in document_fields:
                if field in request.httprequest.files:
                    uploaded_file = request.httprequest.files[field]
                    if uploaded_file and uploaded_file.filename:
                        update_vals[field] = base64.b64encode(uploaded_file.read())
                        update_vals[f'{field}_filename'] = uploaded_file.filename
            
            # Update partner
            if update_vals:
                partner.write(update_vals)
            
            return request.redirect('/my/contact?success=1')
            
        except Exception as e:
            return request.redirect('/my/contact?error=1')
    
    @http.route('/my/documents/status', type='http', auth='user', website=True)
    def documents_status(self):
        """Show document completion status"""
        partner = request.env.user.partner_id
        doc_status = partner.get_portal_documents_status()
        
        return f"""
        <h1>Document Completion Status</h1>
        <div style="margin: 20px 0;">
            <div style="background: #f0f0f0; height: 20px; border-radius: 10px;">
                <div style="background: #875A7B; height: 100%; width: {doc_status['completion_rate']}%; 
                          border-radius: 10px; text-align: center; color: white;">
                    {doc_status['completion_rate']:.1f}%
                </div>
            </div>
        </div>
        
        <h3>✅ Completed Documents:</h3>
        <ul>
            {''.join(f'<li>{doc}</li>' for doc in doc_status['completed'])}
        </ul>
        
        <h3>📋 Pending Documents:</h3>
        <ul>
            {''.join(f'<li>{doc}</li>' for doc in doc_status['pending'])}
        </ul>
        
        <a href="/my/contact" class="btn btn-primary">Update Documents</a>
        """