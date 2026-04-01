from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Backfill: Generate Training Paths (Channels) for existing Stations 
    that do not have one yet.
    """
    stations = env['mcd.soc.station'].search([('channel_id', '=', False)])
    created_count = 0
    
    for station in stations:
        # Check by name first to link existing
        existing_channel = env['slide.channel'].search([('name', '=', station.name)], limit=1)
        
        if existing_channel:
            station.write({'channel_id': existing_channel.id})
            if not existing_channel.soc_station_id:
                existing_channel.write({'soc_station_id': station.id})
        else:
            channel = env['slide.channel'].create({
                'name': station.name,
                'is_published': True,
                'soc_station_id': station.id,
                'description': f"Training Path for Station: {station.name}",
                'enroll': 'public', 
                'channel_type': 'training',
                'promote_strategy': 'most_voted',
            })
            station.write({'channel_id': channel.id})
            created_count += 1
            
    # print(f"SOC Backfill: Linked/Created {len(stations)} training paths.")
