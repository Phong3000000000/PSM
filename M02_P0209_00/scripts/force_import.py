import odoo
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def run_import(env):
    # Import the wizard logic or just copy-paste for simplicity in script
    # Let's import the data directly
    from odoo.addons.M02_P0209_00.models.soc_initial_data import get_initial_soc_data
    
    soc_list = get_initial_soc_data()
    # Filter for Kiosk Host
    targets = [s for s in soc_list if 'Kiosk Host' in s['title']]
    
    if not targets:
        print("Kiosk Host data not found in soc_initial_data!")
        return
        
    print(f"Found {len(targets)} Kiosk Host entries. Importing...")
    
    Channel = env['slide.channel']
    Slide = env['slide.slide']
    SocItem = env['mcd.soc.item']
    SocSection = env['mcd.soc.section']
    
    for soc in targets:
        # 1. Channel
        channel = Channel.search([('name', '=', 'General SOCs')], limit=1) # Or deduce
        # Re-use wizard logic for naming if possible, but hardcoding for safety here
        if soc['area'] == 'service': channel_name = "Service Station"
        else: channel_name = "General SOCs"
        
        channel = Channel.search([('name', '=', channel_name)], limit=1)
        if not channel:
            channel = Channel.create({'name': channel_name, 'is_soc_course': True, 'channel_type': 'training', 'enroll': 'public'})
            
        # 2. Slide
        existing = Slide.search([('name', '=', soc['title']), ('channel_id', '=', channel.id)], limit=1)
        if existing:
            print(f"Slide {soc['title']} already exists.")
            continue
            
        slide = Slide.create({
            'name': soc['title'],
            'channel_id': channel.id,
            'slide_type': 'article',
            'is_soc': True,
            'soc_type': soc['soc_type'],
            'is_published': True
        })
        
        seq = 1
        # Prereqs
        if soc['prerequisites']:
            sec_pre = env['mcd.soc.section'].search([('name', '=', 'Prerequisites')], limit=1)
            if not sec_pre: sec_pre = env['mcd.soc.section'].create({'name': 'Prerequisites'})
            
            for p in soc['prerequisites']:
                SocItem.create({'slide_id': slide.id, 'section_id': sec_pre.id, 'name': p, 'sequence': seq})
                seq += 1
                
        # Sections
        for section in soc['sections']:
            sec_obj = env['mcd.soc.section'].search([('name', '=', section['title'])], limit=1)
            if not sec_obj: sec_obj = env['mcd.soc.section'].create({'name': section['title']})
            
            for q in section['questions']:
                SocItem.create({'slide_id': slide.id, 'section_id': sec_obj.id, 'name': q, 'sequence': seq})
                seq += 1
                
        print(f"Successfully imported {soc['title']}")
        env.cr.commit()

if __name__ == "__main__":
    pass # Managed by Odoo shell
