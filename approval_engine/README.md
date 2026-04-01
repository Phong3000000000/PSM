\# approval\_engine (Odoo 19 Enterprise)



A reusable, upgrade-safe multi-level approval engine that can be embedded into \*\*any\*\* business document model.



\## What you get

\- `approval.mixin` abstract model to add approvals to any model.

\- Configuration:

&nbsp; - `approval.workflow` (per company, per model, active)

&nbsp; - `approval.step` (sequence, approver selection, thresholds, domain, parallel)

\- Runtime:

&nbsp; - `approval.engine.request` + supporting runtime lines (step run + approver run)

&nbsp; - `approval.log` audit trail (and chatter posts)

\- Security:

&nbsp; - Approval Admin / Approval Approver groups

&nbsp; - Access rights + record rules (multi-company safe)

\- Notifications:

&nbsp; - Chatter messages on submit/approve/reject

&nbsp; - Optional email template hooks (placeholder provided)

\- Integration examples (minimal overrides):

&nbsp; - Purchase Order: approval required \*\*before Confirm\*\*

&nbsp; - Invoice/Bill (`account.move`): approval required \*\*before Post\*\*



--

