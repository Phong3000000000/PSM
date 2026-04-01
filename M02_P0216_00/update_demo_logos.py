# update_demo_logos.py - Script to update demo data with partner logos
import base64
import os

# Partner data
partners = {
    'grab': {'name': 'Grab', 'code': 'GRAB', 'desc': 'Nền tảng giao thông và giao hàng hàng đầu Đông Nam Á', 'web': 'https://www.grab.com'},
    'shopee': {'name': 'Shopee', 'code': 'SHOPEE', 'desc': 'Sàn thương mại điện tử hàng đầu Việt Nam', 'web': 'https://shopee.vn'},
    'tch': {'name': 'The Coffee House', 'code': 'TCH', 'desc': 'Chuỗi cà phê hàng đầu Việt Nam', 'web': 'https://www.thecoffeehouse.com'},
    'cgv': {'name': 'CGV Cinemas', 'code': 'CGV', 'desc': 'Hệ thống rạp chiếu phim hàng đầu Việt Nam', 'web': 'https://www.cgv.vn'},
    'kfc': {'name': 'KFC Vietnam', 'code': 'KFC', 'desc': 'Chuỗi thức ăn nhanh quốc tế', 'web': 'https://kfcvietnam.com.vn'},
    'lotte': {'name': 'Lotte Cinema', 'code': 'LOTTE', 'desc': 'Hệ thống rạp chiếu phim Lotte tại Việt Nam', 'web': 'https://www.lottecinemavn.com'}
}

# Generate XML
xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- Urbox Partner Demo Data with Logos -->
'''

for partner_id, data in partners.items():
    # Read and encode logo
    logo_path = f"static/img/partners/{partner_id}.png"
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode()
    else:
        logo_base64 = ""
    
    xml_content += f'''        <record id="partner_{partner_id}" model="urbox.partner">
            <field name="name">{data['name']}</field>
            <field name="code">{data['code']}</field>
            <field name="description">{data['desc']}</field>
            <field name="website">{data['web']}</field>
            <field name="active">True</field>
'''
    if logo_base64:
        xml_content += f'            <field name="logo">{logo_base64}</field>\n'
    
    xml_content += '        </record>\n\n'

xml_content += '''    </data>
</odoo>
'''

# Write to file
with open('data/urbox_partner_demo_data.xml', 'w', encoding='utf-8') as f:
    f.write(xml_content)

print("✅ Demo data updated with logos successfully!")
print(f"Total partners: {len(partners)}")
