# -*- coding: utf-8 -*-
"""
Referral Portal Controller
Routes for candidate registration and employee portal
"""

from odoo import http, _
from odoo.http import request
import base64
import logging

_logger = logging.getLogger(__name__)


class ReferralController(http.Controller):
    
    @http.route('/referral/register/<string:code>', type='http', auth='public', website=True)
    def referral_register_form(self, code, **kw):
        """Public form for candidate to register via referral code"""
        submission = request.env['employee.referral.submission'].sudo().search([
            ('referral_code', '=', code),
            ('state', 'in', ['submitted', 'email_sent'])
        ], limit=1)
        
        if not submission:
            return request.redirect('/404')
        
        return request.render('M02_P0202_03.referral_register_template', {
            'submission': submission,
            'error': kw.get('error'),
            'msg': kw.get('msg', '').replace('+', ' ') if kw.get('msg') else None
        })
    
    @http.route('/referral/register/<string:code>/submit', type='http', auth='public', 
                methods=['POST'], website=True, csrf=True)
    def referral_register_submit(self, code, **post):
        """Process candidate registration form → create hr.applicant"""
        submission = request.env['employee.referral.submission'].sudo().search([
            ('referral_code', '=', code)
        ], limit=1)
        
        if not submission:
            return request.redirect('/404')
        
        try:
            with request.env.cr.savepoint():
                # Prepare applicant values with null-safe checks
                job_name = submission.job_id.name if submission.job_id else 'Vị trí chưa xác định'
                referrer_name = submission.referrer_id.name if submission.referrer_id else 'N/A'

                applicant_vals = {
                    'partner_name': post.get('name'),
                    'email_from': post.get('email'),
                    'partner_phone': post.get('phone'),
                    'job_id': submission.job_id.id if submission.job_id else False,
                    'referral_submission_id': submission.id,
                    # NOTE: do NOT set company_id here — cross-company context causes tx abort
                }

                # Find Interview stage (defensive: catch column-not-found errors)
                interview_stage = False
                try:
                    interview_stage = request.env['hr.recruitment.stage'].sudo().search([
                        ('name', 'ilike', 'interview'),
                        ('recruitment_type', '=', 'store')
                    ], limit=1)
                except Exception:
                    try:
                        interview_stage = request.env['hr.recruitment.stage'].sudo().search([
                            ('name', 'ilike', 'interview'),
                        ], limit=1)
                    except Exception:
                        pass

                if interview_stage:
                    applicant_vals['stage_id'] = interview_stage.id

                # Create Contact (res.partner) for the candidate
                partner_vals = {
                    'name': post.get('name'),
                    'email': post.get('email'),
                    'phone': post.get('phone'),
                    'street': post.get('address', ''),
                    'is_company': False,
                    'type': 'contact',
                    'comment': f"Ngày sinh: {post.get('birthdate', 'N/A')}\nKinh nghiệm: {post.get('experience', 'N/A')}",
                }

                partner = request.env['res.partner'].sudo().create(partner_vals)

                # Read CV file once into memory
                doc_count = 0
                cv_b64 = False
                cv_filename = False
                cv_file = request.httprequest.files.get('cv_file')
                if cv_file and cv_file.filename:
                    cv_b64 = base64.b64encode(cv_file.read())
                    cv_filename = cv_file.filename
                    # Attach to partner
                    request.env['ir.attachment'].sudo().create({
                        'name': f"CV - {cv_filename}",
                        'datas': cv_b64,
                        'res_model': 'res.partner',
                        'res_id': partner.id,
                    })
                    doc_count += 1

                # Link partner to applicant
                applicant_vals['partner_id'] = partner.id

                # Create applicant
                applicant = request.env['hr.applicant'].sudo().create(applicant_vals)

                # Attach CV to applicant as well
                if cv_b64 and cv_filename:
                    request.env['ir.attachment'].sudo().create({
                        'name': f"CV - {cv_filename}",
                        'datas': cv_b64,
                        'res_model': 'hr.applicant',
                        'res_id': applicant.id,
                    })

                # Update submission — also write cv_attachment so backend form shows CV
                submission_vals = {
                    'applicant_id': applicant.id,
                    'state': 'interviewing',
                    'candidate_name': post.get('name'),
                    'candidate_email': post.get('email'),
                    'candidate_phone': post.get('phone'),
                }
                if cv_b64:
                    submission_vals['cv_attachment'] = cv_b64
                    submission_vals['cv_filename'] = cv_filename
                submission.write(submission_vals)

                # Post message with document summary
                submission.message_post(
                    body=_('Ứng viên %s đã hoàn tất đăng ký. Applicant ID: %s. Đã upload %s tài liệu.') % (
                        post.get('name'), applicant.id, doc_count
                    ),
                    message_type='notification'
                )

                _logger.info(f"Candidate registered via referral {code}: {post.get('name')}, Applicant ID: {applicant.id}, Partner ID: {partner.id}, Docs: {doc_count}")

            return request.redirect('/referral/thankyou')

        except Exception as e:
            import traceback
            _logger.error(f"Error processing referral registration: {e}")
            _logger.error(traceback.format_exc())
            error_msg = str(e).replace(' ', '+')[:200]
            return request.redirect(f'/referral/register/{code}?error=1&msg={error_msg}')
    
    @http.route('/referral/thankyou', type='http', auth='public', website=True)
    def referral_thankyou(self, **kw):
        """Thank you page after registration"""
        return request.render('M02_P0202_03.referral_thankyou_template', {})
    
    @http.route('/my/referrals', type='http', auth='user', website=True)
    def my_referrals(self, **kw):
        """Portal: Employee views their referrals and bonus status"""
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', request.env.user.id),
            ('work_contact_id', '=', partner.id)
        ], limit=1)
        
        submissions = []
        if employee:
            submissions = request.env['employee.referral.submission'].sudo().search([
                ('referrer_id', '=', employee.id)
            ], order='create_date desc')
        
        # Count for portal home
        referral_count = len(submissions)
        
        return request.render('M02_P0202_03.portal_my_referrals', {
            'submissions': submissions,
            'referral_count': referral_count,
            'error': kw.get('error'),
            'success': kw.get('success'),
            'msg': kw.get('msg'),
        })
    
    @http.route('/my/referrals/submit', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def my_referrals_submit(self, program_id=None, line_id=None, **post):
        """Portal: Employee submits a new referral"""
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', request.env.user.id),
            ('work_contact_id', '=', partner.id)
        ], limit=1)
        
        if not employee:
            return request.redirect('/my/referrals?error=no_employee')
        
        if request.httprequest.method == 'POST':
            # Process submission
            try:
                # program_id is passed as an argument because it's in the route signature/form data
                pid = program_id or post.get('program_id')
                if not pid:
                     return request.redirect('/my/referrals?error=1&msg=Vui lòng chọn chương trình')
                
                program = request.env['employee.referral.program'].sudo().browse(int(pid))
                if not program or program.state != 'active':
                    return request.redirect('/my/referrals?error=invalid_program')
                
                job_id = post.get('job_id')
                if not job_id:
                     return request.redirect('/my/referrals?error=1&msg=Vui lòng chọn vị trí ứng tuyển')
                
                # Check if job is in program
                valid_job = program.line_ids.filtered(lambda l: str(l.job_id.id) == str(job_id))
                if not valid_job:
                     return request.redirect('/my/referrals?error=1&msg=Vị trí không thuộc chương trình này')

                # Create submission
                vals = {
                    'program_id': program.id,
                    'job_id': int(job_id),
                    'referrer_id': employee.id,
                    'candidate_name': post.get('candidate_name'),
                    'candidate_email': post.get('candidate_email'),
                    'candidate_phone': post.get('candidate_phone'),
                    'notes': post.get('notes'),
                }
                
                # Handle CV upload
                cv_file = request.httprequest.files.get('cv_file')
                if cv_file and cv_file.filename:
                    vals['cv_attachment'] = base64.b64encode(cv_file.read())
                    vals['cv_filename'] = cv_file.filename
                
                submission = request.env['employee.referral.submission'].sudo().create(vals)
                
                # Auto-send email to candidate
                submission.action_send_candidate_email()
                
                _logger.info(f"New referral submission by {employee.name}: {submission.referral_code}")
                
                return request.redirect('/my/referrals?success=1')
                
            except Exception as e:
                _logger.error(f"Error creating referral submission: {e}")
                import traceback
                traceback.print_exc()
                return request.redirect(f'/my/referrals?error=1&msg={e}')
        
        # GET: Show form
        programs = request.env['employee.referral.program'].sudo().search([
            ('state', '=', 'active')
        ])

        # Resolve selected_line from line_id param (for per-position buttons)
        selected_line = None
        selected_program = None
        if line_id:
            selected_line = request.env['employee.referral.program.line'].sudo().browse(int(line_id))
            if not selected_line.exists():
                selected_line = None
            else:
                selected_program = selected_line.program_id
                program_id = selected_program.id

        return request.render('M02_P0202_03.portal_referral_submit', {
            'programs': programs,
            'selected_program_id': int(program_id) if program_id else None,
            'selected_line': selected_line,
            'selected_program': selected_program,
        })
    
    @http.route(['/referral/jobs', '/referral/jobs/page/<int:page>'], type='http', auth='user', website=True)
    def referral_jobs_list(self, page=1, **kw):
        """Job Board: List of active referral programs"""
        Program = request.env['employee.referral.program']
        domain = [('state', '=', 'active')]
        
        # Pager
        url = '/referral/jobs'
        total = Program.sudo().search_count(domain)
        pager = request.website.pager(
            url=url,
            total=total,
            page=page,
            step=10,
            scope=7,
            url_args=kw
        )
        
        programs = Program.sudo().search(domain, limit=10, offset=pager['offset'], order='create_date desc')
        
        return request.render('M02_P0202_03.portal_referral_jobs_list', {
            'programs': programs,
            'pager': pager,
        })
    
    @http.route('/referral/jobs/<int:program_id>', type='http', auth='user', website=True)
    def referral_program_detail(self, program_id, **kw):
        """Job Detail Page"""
        program = request.env['employee.referral.program'].sudo().browse(program_id)
        if not program.exists() or program.state != 'active':
            return request.redirect('/referral/jobs')
            
        return request.render('M02_P0202_03.portal_referral_program_detail', {
            'program': program,
        })