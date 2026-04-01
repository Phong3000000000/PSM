# Food Safety Complaint Management

## Overview
Complete Odoo 19 Enterprise addon for managing food safety complaints in multi-restaurant operations.

## Features
- **Complaint Registration**: Register complaints from stores and customers
- **Product Tracking**: Track both finished products and raw materials (NVL)
- **Multi-Store Support**: Manage complaints across multiple restaurants
- **Fault Analysis**: Identify fault source (restaurant vs supplier)
- **Quality Control Integration**: Link with quality checks and inspections
- **Workflow Management**: Complete workflow from draft to resolution
- **Traceability**: Product and lot number tracking

## Complaint Sources
- **From Store**: Direct complaints from restaurant staff
- **From Customer**: Complaints received from customers

## Food Safety Issue Types
- Contamination
- Foreign Object
- Spoilage/Expiry
- Quality Defect
- Packaging Issue
- Labeling Issue
- Allergen Issue
- Temperature Abuse
- Other

## Workflow States
1. **Draft**: Initial creation
2. **Submitted**: Complaint submitted for review
3. **Under Analysis**: QA team analyzing the issue
4. **Corrective Action**: Actions being taken
5. **Resolved**: Issue resolved
6. **Cancelled**: Complaint cancelled

## Installation
1. Copy the module to your Odoo addons directory
2. Update apps list
3. Install "Food Safety Complaint Management"

## Configuration
1. Assign users to security groups:
   - Food Safety User: Can create and edit complaints
   - Food Safety Manager: Full access including deletion
   - Food Safety QA Inspector: Focus on analysis tasks

## Dependencies
- helpdesk
- quality_control
- stock
- product
- purchase

## Technical
- **Model**: food.safety.complaint
- **Sequence**: FSC/00001
- **Integration**: Mail threading and activities
