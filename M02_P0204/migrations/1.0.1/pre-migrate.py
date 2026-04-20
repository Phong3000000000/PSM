# -*- coding: utf-8 -*-
import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

MODULE_NAME = "M02_P0204"

MODEL_RENAMES = (
    ("interview.schedule", "x_psm_interview_schedule"),
    ("hr.applicant.interview.evaluation", "x_psm_hr_applicant_interview_evaluation"),
    ("hr.applicant.interview.evaluation.section", "x_psm_hr_applicant_interview_evaluation_section"),
    ("hr.applicant.interview.evaluation.line", "x_psm_hr_applicant_interview_evaluation_line"),
    ("hr.applicant.oje.evaluation", "x_psm_hr_applicant_oje_evaluation"),
    ("hr.applicant.oje.evaluation.section", "x_psm_hr_applicant_oje_evaluation_section"),
    ("hr.applicant.oje.evaluation.line", "x_psm_hr_applicant_oje_evaluation_line"),
    ("applicant.get.refuse.reason.line", "x_psm_applicant_get_refuse_reason_line"),
    ("create.job.templates.wizard", "x_psm_create_job_templates_wizard"),
    ("reject.applicant.wizard", "x_psm_reject_applicant_wizard"),
)

# These tables keep model technical names as plain strings.
MODEL_STRING_COLUMNS = (
    ("ir_model_data", "model"),
    ("ir_ui_view", "model"),
    ("ir_actions_act_window", "res_model"),
    ("ir_actions_server", "model_name"),
    ("ir_actions_report", "model"),
    ("mail_template", "model"),
    ("mail_followers", "res_model"),
    ("mail_message", "model"),
    ("mail_activity", "res_model"),
    ("ir_attachment", "res_model"),
    ("ir_filters", "model_id"),
    ("ir_exports", "resource"),
    ("ir_model_relation", "model"),
    ("ir_model_constraint", "model"),
)


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (table_name,))
    return bool(cr.fetchone()[0])


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        (table_name, column_name),
    )
    return bool(cr.fetchone())


def _column_is_textual(cr, table_name, column_name):
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        (table_name, column_name),
    )
    row = cr.fetchone()
    if not row:
        return False
    return row[0] in ("character varying", "text", "character")


def _rename_table_if_needed(cr, old_table, new_table):
    old_exists = _table_exists(cr, old_table)
    new_exists = _table_exists(cr, new_table)

    if not old_exists:
        return

    if new_exists:
        _logger.warning(
            "[0204-MIGRATION] Skip renaming table %s -> %s because target already exists",
            old_table,
            new_table,
        )
        return

    cr.execute(
        SQL(
            "ALTER TABLE %s RENAME TO %s",
            SQL.identifier(old_table),
            SQL.identifier(new_table),
        )
    )
    _logger.info("[0204-MIGRATION] Renamed table %s -> %s", old_table, new_table)


def _update_exact_model_value(cr, table_name, column_name, old_model, new_model):
    if not _table_exists(cr, table_name) or not _column_exists(cr, table_name, column_name):
        return 0

    if not _column_is_textual(cr, table_name, column_name):
        return 0

    cr.execute(
        SQL(
            "UPDATE %s SET %s = %s WHERE %s = %s",
            SQL.identifier(table_name),
            SQL.identifier(column_name),
            new_model,
            SQL.identifier(column_name),
            old_model,
        )
    )
    return cr.rowcount


def _migrate_model_xmlid_name(cr, old_model, new_model):
    if not _table_exists(cr, "ir_model_data"):
        return

    old_name = "model_%s" % old_model.replace(".", "_")
    new_name = "model_%s" % new_model.replace(".", "_")

    # Avoid unique conflicts if a previous failed upgrade already created the new xmlid.
    cr.execute(
        """
        DELETE FROM ir_model_data old
         USING ir_model_data new
         WHERE old.module = %s
           AND old.model = 'ir.model'
           AND old.name = %s
           AND new.module = old.module
           AND new.model = old.model
           AND new.name = %s
        """,
        (MODULE_NAME, old_name, new_name),
    )

    cr.execute(
        """
        UPDATE ir_model_data
           SET name = %s
         WHERE module = %s
           AND model = 'ir.model'
           AND name = %s
        """,
        (new_name, MODULE_NAME, old_name),
    )


def _rename_model_metadata(cr, old_model, new_model):
    touched = 0
    touched += _update_exact_model_value(cr, "ir_model", "model", old_model, new_model)
    touched += _update_exact_model_value(cr, "ir_model_fields", "model", old_model, new_model)
    touched += _update_exact_model_value(cr, "ir_model_fields", "relation", old_model, new_model)

    for table_name, column_name in MODEL_STRING_COLUMNS:
        touched += _update_exact_model_value(cr, table_name, column_name, old_model, new_model)

    _migrate_model_xmlid_name(cr, old_model, new_model)

    if touched:
        _logger.info(
            "[0204-MIGRATION] Updated model references %s -> %s (%s rows)",
            old_model,
            new_model,
            touched,
        )


def migrate(cr, version):
    for old_model, new_model in MODEL_RENAMES:
        old_table = old_model.replace(".", "_")
        new_table = new_model.replace(".", "_")
        _rename_table_if_needed(cr, old_table, new_table)

    for old_model, new_model in MODEL_RENAMES:
        _rename_model_metadata(cr, old_model, new_model)
