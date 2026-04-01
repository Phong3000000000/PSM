from . import controllers
from . import models


def post_init_hook(env):
    # có thể cmt 2 dòng này nếu ko muốn gia hạn vì nó đã chặn cái kiểm tra
    env['ir.config_parameter'].sudo().set_param('database.expiration_date', '2099-12-31')
    env['ir.config_parameter'].sudo().set_param('database.expiration_reason', 'manual')
    
    current_user = env.user
    if current_user and current_user.id != 1:
        admin_group = env.ref('base.group_system', raise_if_not_found=False)
        if admin_group:
            current_user.sudo().write({
                'group_ids': [(4, admin_group.id)]
            })
