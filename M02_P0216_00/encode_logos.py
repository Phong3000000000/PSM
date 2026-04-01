# Script to encode partner logos to base64 for demo data
import base64
import os

partner_folder = "static/img/partners"
partners = ["cgv", "grab", "kfc", "lotte", "shopee", "tch"]

for partner in partners:
    filepath = os.path.join(partner_folder, f"{partner}.png")
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
            print(f"\n<!-- {partner.upper()} Logo -->")
            print(f'<field name="logo">{encoded}</field>')
    else:
        print(f"Missing: {filepath}")
