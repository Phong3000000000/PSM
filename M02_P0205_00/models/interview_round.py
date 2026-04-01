# -*- coding: utf-8 -*-
"""Shared constants for interview round tracking."""

INTERVIEW_ROUND_SELECTION = [
    ('1', 'Vòng 1'),
    ('2', 'Vòng 2'),
    ('3', 'Vòng 3'),
    ('4', 'Vòng 4'),
]

INTERVIEW_STAGE_XML_TO_ROUND = {
    'M02_P0205_00.stage_office_new': '1',
    'M02_P0205_00.stage_office_screening': '1',
    'M02_P0205_00.stage_office_interview_1': '2',
    'M02_P0205_00.stage_office_interview_2': '3',
    'M02_P0205_00.stage_office_interview_3': '4',
    'M02_P0205_00.stage_office_interview_4': '4',
}
