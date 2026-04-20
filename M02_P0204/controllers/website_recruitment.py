# -*- coding: utf-8 -*-
import base64
import json
import html
import logging
import re
import unicodedata

from odoo import _, fields, http
from odoo.http import request
from odoo.tools import email_normalize

_logger = logging.getLogger(__name__)


class WebsiteRecruitmentCustom(http.Controller):
    def _is_file_upload_field(self, field_meta):
        field_meta = field_meta or {}
        field_name = field_meta.get('name')
        field_widget = field_meta.get('widget')
        return field_widget == 'file' or field_name in ('x_cv_attachment', 'x_portrait_image')

    def _get_store_schedule(self, job):
        if job.recruitment_type != 'store':
            return False

        domain = [('state', '=', 'confirmed'), ('week_end_date', '>=', fields.Date.today())]
        if job.department_id:
            domain.append(('department_id', '=', job.department_id.id))
        return request.env['x_psm_interview_schedule'].sudo().search(domain, order='week_start_date asc', limit=1)

    def _normalize_selection_options(self, options):
        normalized = []
        for option in options or []:
            if isinstance(option, (list, tuple)) and len(option) >= 2:
                normalized.append({'value': str(option[0]), 'label': option[1]})
            elif isinstance(option, dict):
                value = option.get('value')
                label = option.get('label') or value
                if value is not None:
                    normalized.append({'value': str(value), 'label': label})
        return normalized

    def _normalize_plain_text(self, value):
        value = value or ''
        value = unicodedata.normalize('NFD', value)
        value = ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn')
        value = value.lower()
        return re.sub(r'[^a-z0-9]+', ' ', value).strip()

    def _get_canonical_document_type_options(self):
        return [
            {'value': 'citizen_id', 'label': 'CCCD'},
            {'value': 'passport', 'label': 'Hộ chiếu'},
        ]

    def _get_canonical_document_type_values(self):
        return {option['value'] for option in self._get_canonical_document_type_options()}

    def _map_document_type_text_to_code(self, raw_value):
        raw_text = str(raw_value or '').strip()
        if not raw_text:
            return False

        if raw_text in self._get_canonical_document_type_values():
            return raw_text

        normalized = self._normalize_plain_text(raw_text)
        if normalized == 'cccd':
            return 'citizen_id'
        if normalized in ('ho chieu', 'passport'):
            return 'passport'
        return False

    def _normalize_document_type_value(self, raw_value, property_fields=None, job=False):
        raw_text = str(raw_value or '').strip()
        if not raw_text:
            return 'citizen_id'

        mapped_direct = self._map_document_type_text_to_code(raw_text)
        if mapped_direct:
            return mapped_direct

        if raw_text.isdigit() and job:
            survey = job._x_psm_get_pre_interview_survey_for_webform()
            if survey:
                answer = request.env['survey.question.answer'].sudo().browse(int(raw_text))
                if answer.exists() and answer.question_id.survey_id.id == survey.id:
                    mapped_from_answer = self._map_document_type_text_to_code(answer.value)
                    if mapped_from_answer:
                        return mapped_from_answer

        document_type_field = next(
            (
                field
                for field in (property_fields or [])
                if isinstance(field, dict) and field.get('name') == 'x_id_document_type'
            ),
            None,
        )

        raw_text_normalized = self._normalize_plain_text(raw_text)
        for option in self._normalize_selection_options((document_type_field or {}).get('selection') or []):
            option_value = str(option.get('value') or '').strip()
            option_label = str(option.get('label') or '').strip()
            option_label_normalized = self._normalize_plain_text(option_label)

            if raw_text != option_value and raw_text_normalized != option_label_normalized:
                continue

            mapped_from_option = (
                self._map_document_type_text_to_code(option_label)
                or self._map_document_type_text_to_code(option_value)
            )
            if mapped_from_option:
                return mapped_from_option

        return raw_text

    def _selection_option_label(self, field_meta, raw_value):
        for option in field_meta.get('selection') or []:
            if str(option.get('value')) == str(raw_value):
                return option.get('label') or ''
        return str(raw_value or '')

    def _resolve_direct_applicant_field(self, field_meta):
        applicant_fields = request.env['hr.applicant']._fields
        field_name = field_meta.get('name')
        if field_name in applicant_fields:
            return field_name

        legacy_alias = {
            'x_psm_current_job': 'x_current_job',
            'x_psm_birthday': 'x_birthday',
            'x_psm_gender': 'x_gender',
            'x_psm_id_document_type': 'x_id_document_type',
            'x_psm_id_number': 'x_id_number',
            'x_psm_education_level': 'x_education_level',
            'x_psm_school_name': 'x_school_name',
            'x_psm_years_experience': 'x_years_experience',
            'x_psm_weekend_available': 'x_weekend_available',
            'x_psm_worked_mcdonalds': 'x_worked_mcdonalds',
            'x_psm_application_content': 'x_application_content',
        }
        aliased = legacy_alias.get(field_name)
        if aliased in applicant_fields:
            return aliased

        normalized_label = self._normalize_plain_text(field_meta.get('label'))
        label_markers = [
            ('ngay sinh', 'x_birthday'),
            ('gioi tinh', 'x_gender'),
            ('danh xung', 'x_salutation'),
            ('loai giay to tuy than', 'x_id_document_type'),
            ('so giay to tuy than', 'x_id_number'),
            ('so cmt cccd ho chieu', 'x_id_number'),
            ('so cmt can cuoc ho chieu', 'x_id_number'),
            ('ngay cap giay to tuy than', 'x_id_issue_date'),
            ('ngay cap cmt cccd ho chieu', 'x_id_issue_date'),
            ('ngay cap cmt can cuoc ho chieu', 'x_id_issue_date'),
            ('noi cap giay to tuy than', 'x_id_issue_place'),
            ('noi cap cmt cccd ho chieu', 'x_id_issue_place'),
            ('noi cap cmt can cuoc ho chieu', 'x_id_issue_place'),
            ('quoc tich', 'x_nationality'),
            ('chieu cao', 'x_height'),
            ('can nang', 'x_weight'),
            ('nguyen quan', 'x_hometown'),
            ('dia chi thuong tru', 'x_permanent_address'),
            ('dia chi hien tai', 'x_current_address'),
            ('trinh do hoc van', 'x_education_level'),
            ('ten truong', 'x_school_name'),
            ('so nam kinh nghiem', 'x_years_experience'),
            ('cong viec hien tai', 'x_current_job'),
            ('cong ty gan nhat', 'x_last_company'),
            ('co the lam viec cuoi tuan', 'x_weekend_available'),
            ('da tung lam viec tai mcdonald', 'x_worked_mcdonalds'),
            ('ma gioi thieu', 'x_referral_staff_id'),
            ('staff id', 'x_referral_staff_id'),
            ('noi dung', 'x_application_content'),
            ('ghi chu them cho nha tuyen dung', 'x_application_content'),
        ]
        for marker, target_field in label_markers:
            if marker in normalized_label and target_field in applicant_fields:
                return target_field

        return False

    def _convert_direct_applicant_field_value(self, field_name, field_meta, raw_value):
        applicant_field = request.env['hr.applicant']._fields.get(field_name)
        if applicant_field and applicant_field.type in ('one2many', 'many2many'):
            return False

        if applicant_field and applicant_field.type == 'many2one':
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                return False

        if field_name in ('x_weekend_available', 'x_worked_mcdonalds'):
            normalized = self._normalize_plain_text(self._selection_option_label(field_meta, raw_value))
            if 'co' in normalized or 'da tung' in normalized:
                return 'yes'
            if 'khong' in normalized or 'chua tung' in normalized:
                return 'no'
            if str(raw_value) in ('yes', 'no'):
                return str(raw_value)
            return False

        if field_name == 'x_gender':
            normalized = self._normalize_plain_text(self._selection_option_label(field_meta, raw_value))
            if 'nam' in normalized:
                return 'male'
            if 'nu' in normalized:
                return 'female'
            if 'khong' in normalized:
                return 'not_display'
            if str(raw_value) in ('male', 'female', 'not_display'):
                return str(raw_value)
            return False

        if field_name == 'x_education_level':
            normalized = self._normalize_plain_text(self._selection_option_label(field_meta, raw_value))
            education_map = [
                ('chua tot nghiep', 'no_degree'),
                ('pho thong', 'high_school'),
                ('trung cap', 'vocational'),
                ('cao dang', 'college'),
                ('dai hoc', 'university'),
                ('thac', 'master'),
                ('tien', 'phd'),
                ('sau dai hoc', 'postgraduate'),
                ('khac', 'others'),
            ]
            for marker, value in education_map:
                if marker in normalized:
                    return value
            allowed_values = {'no_degree', 'high_school', 'vocational', 'college', 'university', 'master', 'phd', 'postgraduate', 'others'}
            if str(raw_value) in allowed_values:
                return str(raw_value)
            return False

        if applicant_field and applicant_field.type == 'selection':
            selection_values = applicant_field.selection
            if callable(selection_values):
                selection_values = selection_values(request.env['hr.applicant'])

            raw_text = str(raw_value or '')
            allowed_keys = {str(key) for key, _label in (selection_values or [])}
            if raw_text in allowed_keys:
                return raw_text

            normalized_raw = self._normalize_plain_text(self._selection_option_label(field_meta, raw_value))
            for key, label in (selection_values or []):
                if normalized_raw and normalized_raw == self._normalize_plain_text(label):
                    return key
            return False

        return self._convert_property_value(field_meta.get('type'), raw_value)

    def _get_survey_property_metadata(self, job):
        metadata_by_name = {}
        has_live_survey = False
        try:
            survey = job._x_psm_get_pre_interview_survey_for_webform()
            if not survey:
                return metadata_by_name, has_live_survey

            has_live_survey = True

            definitions = job._x_psm_get_applicant_properties_definition_from_survey(
                survey=survey,
                include_metadata=True,
            )
            for definition in definitions:
                if not isinstance(definition, dict):
                    continue
                field_name = definition.get('name')
                if field_name:
                    metadata_by_name[field_name] = definition
        except Exception as error_exc:
            _logger.warning('Cannot derive survey property metadata for job %s: %s', job.id, error_exc)
        return metadata_by_name, has_live_survey

    def _build_property_fields(self, job):
        definitions = job.applicant_properties_definition or []
        metadata_by_name, has_live_survey = self._get_survey_property_metadata(job)
        property_fields = []

        for index, definition in enumerate(definitions, start=1):
            if not isinstance(definition, dict):
                continue

            field_type = definition.get('type') or 'char'
            if field_type == 'separator':
                continue

            field_name = definition.get('name')
            if not field_name:
                continue

            if has_live_survey and field_name not in metadata_by_name:
                continue

            metadata = metadata_by_name.get(field_name, {})
            # Prefer metadata derived from the active survey to avoid stale option ids.
            selection = metadata.get('selection') or definition.get('selection')
            correct_selection_values = (
                metadata.get('correct_selection_values')
                or definition.get('correct_selection_values')
                or []
            )

            property_fields.append(
                {
                    'name': field_name,
                    'label': definition.get('string') or field_name.replace('_', ' ').title(),
                    'type': field_type,
                    'required': bool(
                        definition.get('required')
                        or definition.get('is_required')
                        or metadata.get('required')
                    ),
                    'default': definition.get('default'),
                    'selection': self._normalize_selection_options(selection),
                    'sequence': definition.get('sequence', metadata.get('sequence', index * 10)),
                    'is_active': bool(metadata.get('is_active', definition.get('is_active', True))),
                    'mandatory_correct': bool(metadata.get('mandatory_correct') or definition.get('mandatory_correct')),
                    'reject_when_wrong': bool(metadata.get('reject_when_wrong') or definition.get('reject_when_wrong')),
                    'correct_selection_values': [str(value) for value in correct_selection_values],
                    'source_survey_question_id': (
                        metadata.get('source_survey_question_id') or definition.get('source_survey_question_id')
                    ),
                    'source_survey_page_id': (
                        metadata.get('source_survey_page_id') or definition.get('source_survey_page_id')
                    ),
                    'source_survey_page_title': (
                        metadata.get('source_survey_page_title') or definition.get('source_survey_page_title')
                    ),
                }
            )

        return sorted(property_fields, key=lambda item: item.get('sequence', 10))

    def _get_apply_section_config(self):
        return [
            {
                'key': 'basic',
                'title': 'Thông tin cơ bản',
                'field_names': [
                    'partner_name',
                    'email_from',
                    'x_cv_attachment',
                    'x_current_job',
                    'x_portrait_image',
                ],
            },
            {
                'key': 'other',
                'title': 'Các thông tin khác',
                'field_names': [
                    'x_application_content',
                    'x_birthday',
                    'x_salutation',
                    'x_gender',
                    'x_id_document_type',
                    'x_id_number',
                    'x_id_issue_date',
                    'x_id_issue_place',
                    'x_permanent_address',
                    'x_education_level',
                    'x_school_name',
                    'x_hometown',
                    'x_current_address',
                    'x_years_experience',
                    'x_height',
                    'x_weight',
                    'x_nationality',
                ],
            },
            {
                'key': 'additional',
                'title': 'Câu hỏi bổ sung',
                'field_names': [
                    'x_weekend_available',
                    'x_worked_mcdonalds',
                ],
            },
            {
                'key': 'internal',
                'title': 'Câu hỏi nội bộ',
                'field_names': [
                    'x_last_company',
                    'x_referral_staff_id',
                ],
            },
        ]

    def _get_apply_field_catalog(self):
        return {
            'partner_name': {
                'name': 'partner_name',
                'label': 'Họ & tên bạn',
                'type': 'char',
                'required': True,
                'force_render': True,
            },
            'email_from': {
                'name': 'email_from',
                'label': 'Địa chỉ email',
                'type': 'char',
                'required': True,
                'force_render': True,
            },
            'x_cv_attachment': {
                'name': 'x_cv_attachment',
                'label': 'CV của bạn',
                'type': 'char',
                'widget': 'file',
                'required': True,
                'col_size': 12,
                'force_render': True,
            },
            'partner_phone': {
                'name': 'partner_phone',
                'label': 'Số điện thoại',
                'type': 'char',
                'required': False,
            },
            'x_current_job': {
                'name': 'x_current_job',
                'label': 'Công việc hiện tại của bạn',
                'type': 'char',
            },
            'x_portrait_image': {
                'name': 'x_portrait_image',
                'label': 'Ảnh chân dung',
                'type': 'char',
                'widget': 'file',
                'col_size': 12,
                'force_render': False,
            },
            'x_application_content': {
                'name': 'x_application_content',
                'label': 'Nội dung',
                'type': 'text',
            },
            'x_birthday': {
                'name': 'x_birthday',
                'label': 'Ngày tháng năm sinh',
                'type': 'date',
                'required': True,
            },
            'x_salutation': {
                'name': 'x_salutation',
                'label': 'Danh xưng',
                'type': 'selection',
            },
            'x_gender': {
                'name': 'x_gender',
                'label': 'Giới tính (Gender)',
                'type': 'selection',
                'required': True,
                'selection': [
                    {'value': 'male', 'label': 'Nam (Male)'},
                    {'value': 'female', 'label': 'Nữ (Female)'},
                    {'value': 'not_display', 'label': 'Không hiển thị (Not display)'},
                ],
            },
            'x_id_document_type': {
                'name': 'x_id_document_type',
                'label': 'Loại giấy tờ',
                'type': 'selection',
                'required': False,
                'selection': self._get_canonical_document_type_options(),
                'default': 'citizen_id',
                'force_render': False,
            },
            'x_id_number': {
                'name': 'x_id_number',
                'label': 'Số CMT/Căn cước/Hộ chiếu (Social security number/Passport)',
                'type': 'char',
            },
            'x_id_issue_date': {
                'name': 'x_id_issue_date',
                'label': 'Ngày cấp CMT/Căn cước/Hộ chiếu',
                'type': 'date',
                'required': True,
            },
            'x_id_issue_place': {
                'name': 'x_id_issue_place',
                'label': 'Nơi cấp CMT/Căn cước/Hộ chiếu',
                'type': 'char',
                'required': True,
            },
            'x_permanent_address': {
                'name': 'x_permanent_address',
                'label': 'Địa chỉ thường trú',
                'type': 'text',
            },
            'x_education_level': {
                'name': 'x_education_level',
                'label': 'Trình độ học vấn (Education)',
                'type': 'selection',
                'selection': [
                    {'value': 'no_degree', 'label': 'Chưa tốt nghiệp (No degree)'},
                    {'value': 'high_school', 'label': 'Phổ thông (High school)'},
                    {'value': 'vocational', 'label': 'Trung cấp'},
                    {'value': 'college', 'label': 'Cao đẳng (College)'},
                    {'value': 'university', 'label': 'Đại học (University/Academy)'},
                    {'value': 'master', 'label': 'Thạc sỹ (Master)'},
                    {'value': 'phd', 'label': 'Tiến sỹ (PhD)'},
                    {'value': 'postgraduate', 'label': 'Sau đại học (Postgraduate)'},
                    {'value': 'others', 'label': 'Khác (Others)'},
                ],
            },
            'x_school_name': {
                'name': 'x_school_name',
                'label': 'Tên trường Đại học/Cao Đẳng/Trung Cấp (University/Academy)',
                'type': 'char',
                'required': True,
            },
            'x_hometown': {
                'name': 'x_hometown',
                'label': 'Nguyên quán',
                'type': 'text',
            },
            'x_current_address': {
                'name': 'x_current_address',
                'label': 'Địa chỉ hiện tại (Current Address)',
                'type': 'text',
                'required': True,
            },
            'x_years_experience': {
                'name': 'x_years_experience',
                'label': 'Số năm kinh nghiệm',
                'type': 'integer',
            },
            'x_height': {
                'name': 'x_height',
                'label': 'Chiều cao',
                'type': 'float',
            },
            'x_weight': {
                'name': 'x_weight',
                'label': 'Cân nặng',
                'type': 'float',
            },
            'x_nationality': {
                'name': 'x_nationality',
                'label': 'Quốc tịch',
                'type': 'char',
            },
            'x_weekend_available': {
                'name': 'x_weekend_available',
                'label': 'Có thể làm việc cuối tuần và Lễ Tết?',
                'type': 'selection',
                'required': True,
            },
            'x_worked_mcdonalds': {
                'name': 'x_worked_mcdonalds',
                'label': 'Đã từng làm việc tại McDonald’s VN chưa?',
                'type': 'selection',
                'required': True,
            },
            'x_last_company': {
                'name': 'x_last_company',
                'label': 'Công ty gần nhất của bạn là gì?',
                'type': 'char',
                'required': True,
            },
            'x_referral_staff_id': {
                'name': 'x_referral_staff_id',
                'label': 'Nếu bạn được giới thiệu từ Nhân viên McDonald‘s Vietnam, hãy để lại Mã giới thiệu tại đây (Staff ID)',
                'type': 'char',
            },
        }

    def _merge_apply_field(self, base_field, dynamic_field):
        base_field = dict(base_field or {})
        dynamic_field = dict(dynamic_field or {})
        field_name = base_field.get('name') or dynamic_field.get('name')
        is_system_document_type = field_name == 'x_id_document_type'
        if 'required' in dynamic_field:
            required = bool(dynamic_field.get('required'))
        else:
            required = bool(base_field.get('required'))

        merged = {
            'name': field_name,
            'label': base_field.get('label') or dynamic_field.get('label') or dynamic_field.get('string'),
            'type': dynamic_field.get('type') or base_field.get('type') or 'char',
            'required': required,
            'default': (
                'citizen_id'
                if is_system_document_type
                else (
                    dynamic_field.get('default')
                    if dynamic_field.get('default') not in (None, '')
                    else base_field.get('default')
                )
            ),
            'selection': (
                self._get_canonical_document_type_options()
                if is_system_document_type
                else (dynamic_field.get('selection') or base_field.get('selection') or [])
            ),
            'widget': dynamic_field.get('widget') or base_field.get('widget'),
            'sequence': dynamic_field.get('sequence') or base_field.get('sequence') or 999,
            'is_active': bool(dynamic_field.get('is_active', base_field.get('is_active', True))),
            'mandatory_correct': bool(dynamic_field.get('mandatory_correct')),
            'reject_when_wrong': bool(dynamic_field.get('reject_when_wrong')),
            'correct_selection_values': dynamic_field.get('correct_selection_values') or [],
            'source_survey_question_id': dynamic_field.get('source_survey_question_id') or False,
            'source_survey_page_id': dynamic_field.get('source_survey_page_id') or False,
            'source_survey_page_title': dynamic_field.get('source_survey_page_title') or False,
            'col_size': base_field.get('col_size') or dynamic_field.get('col_size'),
            'force_render': bool(base_field.get('force_render')),
        }

        if not merged.get('col_size'):
            if merged.get('widget') == 'file' or merged.get('name') in ('x_cv_attachment', 'x_portrait_image'):
                merged['col_size'] = 12
            elif merged.get('type') in ('text', 'html'):
                merged['col_size'] = 12
            else:
                merged['col_size'] = 6

        return merged if merged.get('name') else False

    def _detect_apply_section_key(self, field):
        field_name = field.get('name') or ''
        direct_map = {
            'partner_name': 'basic',
            'email_from': 'basic',
            'x_cv_attachment': 'basic',
            'partner_phone': 'basic',
            'x_current_job': 'basic',
            'x_portrait_image': 'basic',
            'x_weekend_available': 'additional',
            'x_worked_mcdonalds': 'additional',
            'x_last_company': 'internal',
            'x_referral_staff_id': 'internal',
        }
        if field_name in direct_map:
            return direct_map[field_name]

        normalized_page_title = self._normalize_plain_text(field.get('source_survey_page_title'))
        if 'cau hoi bo sung' in normalized_page_title:
            return 'additional'
        if 'cau hoi noi bo' in normalized_page_title:
            return 'internal'
        if 'thong tin co ban' in normalized_page_title:
            return 'basic'
        return 'other'

    def _build_apply_sections(self, job, property_fields=None):
        property_fields = property_fields if property_fields is not None else self._build_property_fields(job)
        field_catalog = self._get_apply_field_catalog()
        section_config = self._get_apply_section_config()

        section_map = {
            section['key']: {
                'key': section['key'],
                'title': section['title'],
                'fields': [],
            }
            for section in section_config
        }
        dynamic_by_name = {
            field.get('name'): field
            for field in (property_fields or [])
            if isinstance(field, dict) and field.get('name')
        }
        used_field_names = set()

        for section in section_config:
            for order_index, field_name in enumerate(section.get('field_names', []), start=1):
                base_field = field_catalog.get(field_name, {'name': field_name})
                dynamic_field = dynamic_by_name.get(field_name)
                if not dynamic_field and not base_field.get('force_render'):
                    continue

                merged = self._merge_apply_field(base_field, dynamic_field)
                if not merged or merged.get('is_active') is False:
                    continue

                merged['sequence'] = order_index * 10

                section_map[section['key']]['fields'].append(merged)
                used_field_names.add(field_name)

        remaining_fields = sorted(
            [
                field
                for field in (property_fields or [])
                if isinstance(field, dict) and field.get('name') and field.get('name') not in used_field_names
            ],
            key=lambda item: (item.get('sequence', 999), item.get('name')),
        )
        for dynamic_field in remaining_fields:
            if dynamic_field.get('is_active') is False:
                continue

            merged = self._merge_apply_field({}, dynamic_field)
            if not merged:
                continue

            section_key = self._detect_apply_section_key(merged)
            if section_key not in section_map:
                section_key = 'other'
            section_map[section_key]['fields'].append(merged)

        for section in section_map.values():
            section['fields'] = sorted(
                section['fields'],
                key=lambda field: (field.get('sequence', 999), field.get('name')),
            )

        return [section_map[section['key']] for section in section_config]

    def _resolve_live_question_for_field(self, survey, field):
        if not survey:
            return False

        source_question_id = field.get('source_survey_question_id')
        try:
            source_question_id = int(source_question_id)
        except (TypeError, ValueError):
            source_question_id = 0

        if source_question_id:
            question = request.env['survey.question'].sudo().browse(source_question_id)
            if question.exists() and question.survey_id.id == survey.id:
                if (
                    question.survey_id.x_psm_survey_usage == 'pre_interview'
                    and question.x_psm_show_on_webform is False
                ):
                    return False
                return question

        normalized_label = self._normalize_plain_text(field.get('label'))
        if not normalized_label:
            return False

        for question in survey.question_ids.filtered(
            lambda q: not q.is_page
            and (
                survey.x_psm_survey_usage != 'pre_interview'
                or q.x_psm_show_on_webform is not False
            )
        ):
            question_label = self._normalize_plain_text((question.title or question.question or '').strip())
            if question_label and question_label == normalized_label:
                return question

        return False

    def _evaluate_mandatory_selection_field(self, field, raw_value, survey=False):
        raw_value = str(raw_value or '').strip()
        selected_label = self._selection_option_label(field, raw_value)

        correct_values = {
            str(value)
            for value in (field.get('correct_selection_values') or [])
            if value not in (None, '')
        }
        correct_labels = []

        question = self._resolve_live_question_for_field(survey, field) if survey else False
        if question and question.question_type == 'simple_choice':
            suggested_answers = question.suggested_answer_ids.sorted('sequence')
            selected_answer = suggested_answers.filtered(lambda a: str(a.id) == raw_value)[:1]
            if selected_answer:
                selected_label = selected_answer.value or selected_label

            correct_answers = suggested_answers.filtered('is_correct')
            live_correct_values = {str(answer.id) for answer in correct_answers}
            live_correct_labels = [answer.value for answer in correct_answers if answer.value]

            if live_correct_values:
                correct_values = live_correct_values
            if live_correct_labels:
                correct_labels = live_correct_labels

        if not correct_labels:
            option_by_value = {
                str(option.get('value')): (option.get('label') or '')
                for option in (field.get('selection') or [])
                if option.get('value') is not None
            }
            correct_labels = [
                option_by_value[value]
                for value in correct_values
                if option_by_value.get(value)
            ]

        selected_label_normalized = self._normalize_plain_text(selected_label)
        normalized_correct_labels = {
            self._normalize_plain_text(label)
            for label in correct_labels
            if label
        }

        has_expected_answer = bool(correct_values or normalized_correct_labels)
        is_correct_by_id = bool(raw_value and correct_values and raw_value in correct_values)
        is_correct_by_text = bool(
            not is_correct_by_id
            and selected_label_normalized
            and normalized_correct_labels
            and selected_label_normalized in normalized_correct_labels
        )
        is_correct = bool(not has_expected_answer or is_correct_by_id or is_correct_by_text)
        result = 'passed'
        if not is_correct:
            result = 'reject' if field.get('reject_when_wrong') else 'review'

        return {
            'field_name': field.get('name'),
            'question_label': field.get('label') or field.get('name'),
            'selected_value': raw_value or False,
            'selected_answer': selected_label or '',
            'correct_values': sorted(correct_values),
            'correct_answers': correct_labels,
            'mandatory_correct': bool(field.get('mandatory_correct')),
            'reject_when_wrong': bool(field.get('reject_when_wrong')),
            'source_survey_question_id': field.get('source_survey_question_id') or False,
            'matched_by': (
                'id'
                if is_correct_by_id
                else ('text' if is_correct_by_text else ('skip' if not has_expected_answer else False))
            ),
            'is_correct': is_correct,
            'result': result,
        }

    def _build_application_review_payload(self, review_lines):
        normalized_lines = []
        for line in review_lines or []:
            if not isinstance(line, dict):
                continue

            result = line.get('result')
            if result not in ('passed', 'review', 'reject'):
                result = 'passed'

            line_is_correct = line.get('is_correct')
            if line_is_correct is None:
                line_is_correct = (result == 'passed')

            normalized_lines.append(
                {
                    'field_name': line.get('field_name'),
                    'question_label': line.get('question_label') or line.get('field_name'),
                    'selected_value': line.get('selected_value') or False,
                    'selected_answer': line.get('selected_answer') or '',
                    'correct_values': line.get('correct_values') or [],
                    'correct_answers': line.get('correct_answers') or [],
                    'mandatory_correct': bool(line.get('mandatory_correct')),
                    'reject_when_wrong': bool(line.get('reject_when_wrong')),
                    'source_survey_question_id': line.get('source_survey_question_id') or False,
                    'matched_by': line.get('matched_by') or False,
                    'is_correct': bool(line_is_correct),
                    'result': result,
                }
            )

        if not normalized_lines:
            return False

        summary = {
            'total': len(normalized_lines),
            'passed': len([line for line in normalized_lines if line['result'] == 'passed']),
            'review': len([line for line in normalized_lines if line['result'] == 'review']),
            'reject': len([line for line in normalized_lines if line['result'] == 'reject']),
        }

        return {
            'version': 1,
            'lines': normalized_lines,
            'summary': summary,
        }

    def _build_failed_questions_html(self, review_questions, reject_questions):
        sections = []

        if review_questions:
            review_lines = "".join(
                f"<li>{html.escape(question_label)}</li>"
                for question_label in review_questions
            )
            sections.append(
                "<p><strong>Sai cau 'Phai dung' (dua vao Under Review):</strong></p>"
                f"<ul>{review_lines}</ul>"
            )

        if reject_questions:
            reject_lines = "".join(
                f"<li>{html.escape(question_label)}</li>"
                for question_label in reject_questions
            )
            sections.append(
                "<p><strong>Sai cau 'Loai khi sai' (Reject ngay):</strong></p>"
                f"<ul>{reject_lines}</ul>"
            )

        return "".join(sections) or False

    def _find_pipeline_stage(self, applicant, stage_name):
        stage_type = False
        if hasattr(applicant, '_get_pipeline_stage_type'):
            stage_type = applicant._get_pipeline_stage_type()
        if applicant.recruitment_type == 'store' and not stage_type:
            return request.env['hr.recruitment.stage']

        Stage = request.env['hr.recruitment.stage'].sudo()

        domain = [('name', '=', stage_name)]
        if stage_type:
            domain.append(('recruitment_type', '=', stage_type))
        stage = Stage.search(domain, limit=1)
        if stage:
            return stage

        ilike_domain = [('name', 'ilike', stage_name)]
        if stage_type:
            ilike_domain.append(('recruitment_type', '=', stage_type))
        stage = Stage.search(ilike_domain, limit=1)
        if stage:
            return stage

        return request.env['hr.recruitment.stage']

    def _apply_application_form_outcome(self, applicant, review_questions, reject_questions, review_lines=None):
        failed_html = self._build_failed_questions_html(review_questions, reject_questions)
        review_payload = self._build_application_review_payload(review_lines)
        outcome_vals = {
            'failed_mandatory_questions': failed_html,
            'application_form_review_payload': (
                json.dumps(review_payload, ensure_ascii=False) if review_payload else False
            ),
        }

        if reject_questions:
            reject_stage = self._find_pipeline_stage(applicant, 'Reject')
            if reject_stage:
                outcome_vals['stage_id'] = reject_stage.id
            outcome_vals.update(
                {
                    'survey_under_review_date': False,
                    'reject_reason': (
                        "Tu dong loai do sai cau 'Loai khi sai': "
                        + ", ".join(reject_questions)
                    ),
                }
            )
            if 'x_psm_0205_document_approval_status' in applicant._fields:
                outcome_vals['x_psm_0205_document_approval_status'] = 'refused'
            applicant.sudo().write(outcome_vals)
            return 'reject'

        if review_questions:
            review_stage = self._find_pipeline_stage(applicant, 'Under Review')
            if review_stage:
                outcome_vals['stage_id'] = review_stage.id
            outcome_vals.update(
                {
                    'survey_under_review_date': fields.Datetime.now(),
                }
            )
            if 'x_psm_0205_document_approval_status' in applicant._fields:
                outcome_vals['x_psm_0205_document_approval_status'] = 'pending'
            applicant.sudo().write(outcome_vals)
            return 'under_review'

        applicant.sudo().write(outcome_vals)
        return 'pass'

    def _convert_property_value(self, field_type, raw_value):
        if field_type == 'boolean':
            return bool(raw_value)

        if raw_value in (None, ''):
            return False

        if field_type == 'integer':
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                return 0

        if field_type in ('float', 'monetary'):
            try:
                return float(raw_value)
            except (TypeError, ValueError):
                return 0.0

        # Keep raw string for char/text/date/datetime/selection and unsupported public-field types.
        return raw_value

    def _normalize_email_for_duplicate_check(self, raw_email):
        stripped_email = (raw_email or '').strip()
        normalized_email = email_normalize(stripped_email) or stripped_email.lower()
        return stripped_email, normalized_email

    def _is_rejected_applicant_for_reapply(self, applicant):
        if (getattr(applicant, 'x_psm_0205_document_approval_status', '') or '').lower() == 'refused':
            return True

        stage_name = (applicant.stage_id.name or '').strip().lower()
        return 'reject' in stage_name

    def _find_duplicate_applicants_for_job_email(self, job, submitted_email):
        raw_email, normalized_email = self._normalize_email_for_duplicate_check(submitted_email)
        if not (raw_email or normalized_email):
            return request.env['hr.applicant'].browse()

        email_domain_parts = []
        if normalized_email:
            email_domain_parts.extend(
                [
                    ('email_normalized', '=', normalized_email),
                    ('email_from', 'ilike', normalized_email),
                ]
            )
        if raw_email and raw_email.lower() != normalized_email:
            email_domain_parts.append(('email_from', 'ilike', raw_email))

        domain = [('job_id', '=', job.id)]
        if email_domain_parts:
            if len(email_domain_parts) == 1:
                domain.append(email_domain_parts[0])
            else:
                domain.extend(['|'] * (len(email_domain_parts) - 1))
                domain.extend(email_domain_parts)

        candidates = request.env['hr.applicant'].sudo().with_context(active_test=False).search(domain)
        target_email = normalized_email or raw_email.lower()
        duplicates = request.env['hr.applicant'].browse()

        for applicant in candidates:
            email_normalized_value = (applicant.email_normalized or '').strip().lower()
            email_legacy_value = (applicant.email_from or '').strip().lower()
            email_from_normalized = (email_normalize(applicant.email_from or '') or '').strip().lower()

            # Legacy fallback: compare lower(trim(email_from)) when normalized value is missing/dirty.
            if (
                email_normalized_value == target_email
                or email_from_normalized == target_email
                or email_legacy_value == target_email
            ):
                duplicates |= applicant

        return duplicates

    def _render_apply_page(self, job, error=None, default=None):
        job_sudo = job.sudo()
        property_fields = self._build_property_fields(job_sudo)
        return request.render(
            'M02_P0204.website_job_apply_custom',
            {
                'job': job,
                'main_object': job_sudo,
                'property_fields': property_fields,
                'apply_sections': self._build_apply_sections(job_sudo, property_fields=property_fields),
                'schedule': self._get_store_schedule(job_sudo),
                'error': error or {},
                'default': default or {},
            },
        )

    @http.route('/jobs/apply/<model("hr.job"):job>', type='http', auth='public', website=True)
    def website_job_apply_custom(self, job, **kwargs):
        if not job or not job.active:
            return request.render('website_hr_recruitment.index')
        return self._render_apply_page(job)

    @http.route('/jobs/apply/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def website_job_apply_submit(self, **post):
        job_id = int(post.get('job_id', 0))
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists():
            return request.redirect('/jobs')

        error = {}
        default = {key: value for key, value in post.items() if isinstance(value, str)}
        property_fields = self._build_property_fields(job)
        for field in property_fields:
            if self._is_file_upload_field(field):
                default.pop(field.get('name'), None)

        partner_name = (post.get('partner_name') or '').strip()
        email_from = (post.get('email_from') or '').strip()
        linkedin_profile = (post.get('linkedin_profile') or '').strip()
        x_id_number = (post.get('x_id_number') or '').strip()
        x_id_document_type = self._normalize_document_type_value(
            post.get('x_id_document_type'),
            property_fields=property_fields,
            job=job,
        )
        default['x_id_document_type'] = x_id_document_type
        allowed_document_types = self._get_canonical_document_type_values()
        cv_file = post.get('x_cv_attachment')

        if not partner_name:
            error['partner_name'] = _('Vui lòng nhập họ và tên.')
        if not email_from:
            error['email_from'] = _('Vui lòng nhập email liên hệ.')
        if not cv_file or not getattr(cv_file, 'filename', False):
            error['x_cv_attachment'] = _('Vui lòng tải CV/Hồ sơ đính kèm trước khi nộp.')
        if x_id_document_type not in allowed_document_types:
            error['x_id_document_type'] = _('Loại giấy tờ không hợp lệ.')
        if x_id_number and x_id_document_type in allowed_document_types:
            if x_id_document_type == 'citizen_id' and not re.match(r'^\d{12}$', x_id_number):
                error['x_id_number'] = _('CCCD phải gồm đúng 12 chữ số.')
            elif x_id_document_type == 'passport' and not re.match(r'^[A-Za-z0-9]{6,12}$', x_id_number):
                error['x_id_number'] = _('Hộ chiếu chỉ gồm chữ và số, độ dài từ 6 đến 12 ký tự.')

        for field in property_fields:
            if field.get('is_active') is False:
                continue
            if self._is_file_upload_field(field):
                continue
            if not field.get('required'):
                continue
            raw_value = post.get(field['name'])
            if field['type'] == 'boolean':
                if not raw_value:
                    error[field['name']] = _('Trường này là bắt buộc.')
            elif raw_value in (None, ''):
                error[field['name']] = _('Trường này là bắt buộc.')

        if error:
            error['_form'] = _('Vui lòng điền đầy đủ các trường bắt buộc trước khi nộp hồ sơ.')

        failed_review_questions = []
        failed_reject_questions = []
        review_lines = []
        live_survey = job._x_psm_get_pre_interview_survey_for_webform()

        for field in property_fields:
            if field.get('is_active') is False:
                continue
            if not field.get('mandatory_correct'):
                continue
            if field.get('type') != 'selection':
                continue

            raw_value = post.get(field['name'])
            if not raw_value:
                continue

            review_line = self._evaluate_mandatory_selection_field(field, raw_value, survey=live_survey)
            review_lines.append(review_line)

            # Canonical decision comes from `result`; keep this resilient even if
            # future payloads miss `is_correct`.
            review_result = review_line.get('result') or 'passed'
            if review_result not in ('review', 'reject'):
                continue

            if review_result == 'reject':
                failed_reject_questions.append(review_line.get('question_label') or field.get('name'))
            else:
                failed_review_questions.append(review_line.get('question_label') or field.get('name'))

        # Safety net: nếu toàn bộ câu mandatory-correct đều pass thì tuyệt đối
        # không được giữ danh sách failed (tránh lệch popup/banner do dữ liệu cũ).
        if review_lines and all((line.get('result') or 'passed') == 'passed' for line in review_lines):
            failed_review_questions = []
            failed_reject_questions = []

        if error:
            return self._render_apply_page(job, error=error, default=default)

        duplicate_applicants = self._find_duplicate_applicants_for_job_email(job, email_from)
        blocking_applicants = duplicate_applicants.filtered(
            lambda applicant: not self._is_rejected_applicant_for_reapply(applicant)
        )
        if blocking_applicants:
            duplicate_error_message = _(
                'Email này đã ứng tuyển job này rồi, chỉ được nộp lại khi hồ sơ cũ đã bị từ chối.'
            )
            error['email_from'] = duplicate_error_message
            error['_form'] = duplicate_error_message
            return self._render_apply_page(job, error=error, default=default)

        applicant_vals = {
            'job_id': job.id,
            'application_source': 'web',
            'partner_name': partner_name,
            'email_from': email_from,
            'linkedin_profile': linkedin_profile or False,
        }
        if x_id_number and 'x_id_number' in request.env['hr.applicant']._fields:
            applicant_vals['x_id_number'] = x_id_number
        if 'x_id_document_type' in request.env['hr.applicant']._fields:
            applicant_vals['x_id_document_type'] = x_id_document_type

        if job.recruitment_type == 'store' and 'x_psm_0205_document_approval_status' in request.env['hr.applicant']._fields:
            applicant_vals['x_psm_0205_document_approval_status'] = 'approved'

        properties_vals = {}
        for field in property_fields:
            if field.get('is_active') is False:
                continue
            if self._is_file_upload_field(field):
                continue
            raw_value = post.get(field['name'])
            has_input = field['type'] == 'boolean' or raw_value not in (None, '')
            if not has_input:
                continue

            direct_field = self._resolve_direct_applicant_field(field)
            if direct_field:
                converted_direct = self._convert_direct_applicant_field_value(direct_field, field, raw_value)
                if converted_direct not in (False, None, '') or str(raw_value) == '0' or field['type'] == 'boolean':
                    applicant_vals[direct_field] = converted_direct
                    continue

                converted_fallback = self._convert_property_value(field['type'], raw_value)
                if converted_fallback not in (False, None, '') or str(raw_value) == '0' or field['type'] == 'boolean':
                    properties_vals[field['name']] = converted_fallback
                continue

            converted = self._convert_property_value(field['type'], raw_value)
            if converted not in (False, None, '') or str(raw_value) == '0' or field['type'] == 'boolean':
                properties_vals[field['name']] = converted

        if properties_vals:
            applicant_vals['applicant_properties'] = properties_vals

        applicant = request.env['hr.applicant'].sudo().create(applicant_vals)

        portrait_file = post.get('x_portrait_image')
        if portrait_file and hasattr(portrait_file, 'read') and 'x_portrait_image' in applicant._fields:
            try:
                if hasattr(portrait_file, 'seek'):
                    portrait_file.seek(0)
                image_data = portrait_file.read()
                if image_data:
                    applicant.sudo().write({'x_portrait_image': base64.b64encode(image_data)})
            except Exception as error_exc:
                _logger.error('Failed to save portrait image for applicant %s: %s', applicant.id, error_exc)

        if cv_file and hasattr(cv_file, 'read'):
            try:
                if hasattr(cv_file, 'seek'):
                    cv_file.seek(0)
                cv_data = cv_file.read()
                if cv_data:
                    request.env['ir.attachment'].sudo().create(
                        {
                            'name': cv_file.filename if hasattr(cv_file, 'filename') else 'cv_attachment',
                            'res_model': 'hr.applicant',
                            'res_id': applicant.id,
                            'type': 'binary',
                            'datas': base64.b64encode(cv_data),
                        }
                    )
            except Exception as error_exc:
                _logger.error('Failed to save CV attachment for applicant %s: %s', applicant.id, error_exc)

        application_outcome = self._apply_application_form_outcome(
            applicant,
            failed_review_questions,
            failed_reject_questions,
            review_lines=review_lines,
        )

        if job.recruitment_type == 'store' and application_outcome == 'pass':
            target_name = 'Interview & OJE' if job.position_level == 'staff' else 'Interview'
            pass_stage = request.env['hr.applicant']._get_target_pipeline_stage(
                target_name,
                recruitment_type='store',
                position_level=job.position_level,
            )
            if pass_stage:
                applicant.sudo().write({'stage_id': pass_stage.id})

        interview_slot = post.get('interview_slot')
        schedule_id = post.get('schedule_id')
        if job.recruitment_type == 'store' and interview_slot and schedule_id and schedule_id.isdigit():
            schedule = request.env['x_psm_interview_schedule'].sudo().browse(int(schedule_id))
            if schedule.exists():
                # Lưu slot/schedule ngay cả khi hồ sơ vào Under Review, để khi HR duyệt có thể auto-book.
                applicant.sudo().write(
                    {
                        'interview_booked_slot': interview_slot,
                        'interview_schedule_id': schedule.id,
                    }
                )

                if application_outcome == 'pass' and applicant.stage_id and 'interview' in (applicant.stage_id.name or '').lower():
                    try:
                        # Keep submit transaction healthy even if auto-book raises SQL errors.
                        with request.env.cr.savepoint():
                            booking_result = applicant.action_auto_book_interview_from_survey()
                            _logger.info('[AUTO_BOOK] Applicant %s booking_result=%s', applicant.id, booking_result)
                    except Exception as error_exc:
                        _logger.exception(
                            '[AUTO_BOOK] Failed applicant %s: %s',
                            applicant.id,
                            getattr(error_exc, 'name', str(error_exc)),
                        )

                    request.env['bus.bus']._sendone(
                        f'interview_slots_{schedule.id}',
                        'slot_update',
                        schedule.get_slot_availability(),
                    )

        job_sudo = job.sudo()
        if job.recruitment_type == 'store':
            try:
                note = (
                    f"<p><b>Ứng viên mới:</b> {applicant.partner_name or applicant.name or 'Chưa rõ'}</p>"
                    f"<p><b>Vị trí:</b> {job.name}</p>"
                    '<p><b>Nguồn:</b> Website Portal</p>'
                    '<p>Vui lòng kiểm tra hồ sơ và xử lý bước tiếp theo.</p>'
                )
                applicant_store = applicant.sudo()
                if hasattr(applicant_store, '_schedule_store_hr_activity'):
                    applicant_store._schedule_store_hr_activity(
                        summary=f'Hồ sơ ứng tuyển mới: {applicant.partner_name or applicant.name or "Ứng viên"}',
                        note=note,
                        activity_label='website_apply_submit',
                    )
                else:
                    _logger.warning(
                        'Store applicant activity helper is unavailable for applicant %s; activity is skipped.',
                        applicant.id,
                    )
            except Exception as error_exc:
                _logger.error('Failed to create store applicant activity for applicant %s: %s', applicant.id, error_exc)
        else:
            target_user = applicant.sudo().user_id or job_sudo.user_id
            if not target_user and job_sudo.department_id.manager_id.user_id:
                target_user = job_sudo.department_id.manager_id.user_id
            if not target_user:
                target_user = request.env.ref('base.user_admin', raise_if_not_found=False)

            if target_user:
                try:
                    note = (
                        f"<p><b>Ứng viên mới:</b> {applicant.partner_name or applicant.name or 'Chưa rõ'}</p>"
                        f"<p><b>Vị trí:</b> {job.name}</p>"
                        '<p><b>Nguồn:</b> Website Portal</p>'
                        '<p>Vui lòng kiểm tra hồ sơ và xử lý bước tiếp theo.</p>'
                    )
                    applicant.sudo().activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=target_user.id,
                        summary=f'Hồ sơ ứng tuyển mới: {applicant.partner_name or applicant.name or "Ứng viên"}',
                        note=note,
                        date_deadline=fields.Date.context_today(applicant),
                    )
                except Exception as error_exc:
                    _logger.error('Failed to create applicant activity for applicant %s: %s', applicant.id, error_exc)

        return request.render(
            'M02_P0204.website_apply_thankyou',
            {
                'job': job,
                'applicant': applicant,
            },
        )
