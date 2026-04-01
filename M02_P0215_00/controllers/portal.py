from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
import datetime


class DisciplinePortal(CustomerPortal):
    def _get_employee_from_user(self):
        """
        Helper method to find the employee linked to the current user.
        Priority 1: Linked via user_id field in hr.employee
        Priority 2: Matched via work_email == user.login (or user.email)
        """
        user = request.env.user
        Employee = request.env["hr.employee"].sudo()

        # 1. Try direct link
        employee = Employee.search([("user_id", "=", user.id)], limit=1)
        if employee:
            return employee

        # 2. Try email match (Common for Portal Users)
        # Check both login and email just to be safe
        emails_to_check = [user.login, user.email]
        emails_to_check = [e for e in emails_to_check if e]  # Filter None

        if emails_to_check:
            employee = Employee.search([("work_email", "in", emails_to_check)], limit=1)

        return employee

    @http.route(["/my", "/my/home"], type="http", auth="user", website=True)
    def home(self, **kw):
        return super().home(**kw)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        print(f"DEBUG PORTAL HOME: Counters requested: {counters}")

        if "discipline_count" in counters or not counters:
            # Smart Lookup
            employee = self._get_employee_from_user()
            if employee:
                domain = [("employee_id", "=", employee.id)]
                count = request.env["hr.discipline.record"].sudo().search_count(domain)
                values["discipline_count"] = count
                print(
                    f"DEBUG PORTAL HOME: Discipline Count Computed: {count} (Employee: {employee.name})"
                )
            else:
                values["discipline_count"] = 0
                print("DEBUG PORTAL HOME: No Employee Found for this User")

        return values

    @http.route(
        ["/my/disciplines", "/my/disciplines/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_disciplines(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kw
    ):
        values = self._prepare_portal_layout_values()
        HrDisciplineRecord = request.env["hr.discipline.record"].sudo()

        # Smart Lookup
        employee = self._get_employee_from_user()

        if employee:
            domain = [("employee_id", "=", employee.id)]
        else:
            # If no employee found, show nothing
            domain = [("id", "=", -1)]

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "date desc"},
            "name": {"label": _("Reference"), "order": "name"},
        }
        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        # Count for pager
        discipline_count = HrDisciplineRecord.search_count(domain)

        # Pager logic
        pager = portal_pager(
            url="/my/disciplines",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=discipline_count,
            page=page,
            step=10,
        )

        # Content
        disciplines = HrDisciplineRecord.search(
            domain, order=order, limit=10, offset=pager["offset"]
        )

        values.update(
            {
                "date": date_begin,
                "disciplines": disciplines,
                "page_name": "discipline",
                "pager": pager,
                "default_url": "/my/disciplines",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("M02_P0215_00.portal_my_disciplines", values)

    @http.route(
        ["/my/discipline/<int:record_id>"], type="http", auth="user", website=True
    )
    def portal_discipline_view(self, record_id, **kw):
        record = request.env["hr.discipline.record"].sudo().browse(record_id)

        # Smart Lookup for security check
        current_employee = self._get_employee_from_user()

        # Security Check:
        # Allow if record exists AND belongs to the identified employee
        if (
            not record.exists()
            or not current_employee
            or record.employee_id != current_employee
        ):
            print("DEBUG PORTAL: ACCESS DENIED -> Redirecting")
            return request.redirect("/my")

        values = {
            "record": record,
            "page_name": "discipline_form",
        }
        return request.render(
            "M02_P0215_00.portal_discipline_explanation_template", values
        )

    @http.route(
        ["/my/discipline/submit"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_discipline_submit(self, **post):
        record_id = int(post.get("record_id"))

        record = request.env["hr.discipline.record"].sudo().browse(record_id)
        current_employee = self._get_employee_from_user()

        if (
            record.state == "waiting_explanation"
            and current_employee
            and record.employee_id == current_employee
        ):
            # Extract Data
            incident_date_time_str = post.get("incident_date_time")
            if incident_date_time_str:
                incident_date_time_str = incident_date_time_str.replace("T", " ")

            explanation_content = post.get("employee_explanation")
            signature_data = post.get("employee_signature") or False

            # Create explanation entry for history tracking
            explanation_sequence = len(record.explanation_ids) + 1
            request.env["hr.discipline.explanation"].sudo().create(
                {
                    "record_id": record.id,
                    "sequence": explanation_sequence,
                    "incident_date_time": incident_date_time_str,
                    "incident_location": post.get("incident_location"),
                    "witness_names": post.get("witness_names"),
                    "explanation_content": explanation_content,
                    "explanation_reason": post.get("explanation_reason"),
                    "explanation_commitment": post.get("explanation_commitment"),
                    "employee_signature": signature_data,
                    "state": "submitted",
                    "submitted_date": datetime.datetime.now(),
                }
            )

            # Also update the main record for backward compatibility
            val_updates = {
                "incident_date_time": incident_date_time_str,
                "incident_location": post.get("incident_location"),
                "witness_names": post.get("witness_names"),
                "employee_explanation": explanation_content,
                "explanation_reason": post.get("explanation_reason"),
                "explanation_commitment": post.get("explanation_commitment"),
                "employee_signature": signature_data,
                "explanation_date": datetime.date.today(),
                "state": "manager_review",
            }
            record.write(val_updates)

            record.message_post(
                body=f"Nhân viên đã gửi tường trình lần thứ {explanation_sequence}",
                subject="Explanation Received",
            )

        return request.redirect(f"/my/discipline/{record_id}?success=True")
