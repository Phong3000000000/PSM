{
    "name": "M02_P0201_OO - Approval Travel Request Extension",
    "version": "1.0.0",
    "category": "Approvals",
    "summary": "Require employee personal info for travel approval",
    "depends": [
        "approvals",
        "hr",
        "M01_P0103_00",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/approval_category_view.xml",
        "views/travel_province_view.xml",
        "views/travel_hotel_view.xml",
        "views/approval_flight_config_views.xml",
        "views/approval_request_view.xml",
        "views/business_trip_report_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}