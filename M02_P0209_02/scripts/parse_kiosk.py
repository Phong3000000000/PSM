import os
import openpyxl
import pprint

FILE_PATH = "/mnt/extra-addons/M02_P0209_01/gdrive_data/Kiosk Host.xlsx"

def parse_single():
    if not os.path.exists(FILE_PATH):
        print("File not found")
        return

    wb = openpyxl.load_workbook(FILE_PATH, data_only=True)
    ws = wb.active
    
    data = {
        'title': 'Kiosk Host (Dining)',
        'code': '',
        'soc_type': 'bsoc',
        'area': 'service',
        'sub_area': 'other', # Dining
        'prerequisites': [],
        'sections': []
    }
    
    parsing_mode = None
    sections_list = []
    
    for row in ws.iter_rows(values_only=True):
        if not row or not any(row): continue
        row_str = " ".join([str(c) for c in row if c]).lower()
        
        if 'bước 1' in row_str:
            parsing_mode = 'prereq'
            continue
        elif 'bước 2' in row_str or 'bước 3' in row_str or 'quy trình' in row_str:
            parsing_mode = 'procedure'
            continue
            
        content = next((str(c) for c in row if c), None)
        if not content: continue
        content = content.strip()
        
        if parsing_mode == 'prereq':
            if len(content) > 5 and 'verify' not in content.lower():
                data['prerequisites'].append(content)
        elif parsing_mode == 'procedure':
            if content.lower() in ['y', 'n', 'n/a', 'pass', 'fail']: continue
            if len(content) < 3: continue
            
            is_header = False
            if content.lower() in ['chuẩn bị quầy', 'vệ sinh', 'thực hiện', 'service', 'an toàn thực phẩm', 'chào khách hàng', 'lấy order', 'thanh toán', 'cayg & stock-up']:
                is_header = True
                
            if is_header:
                sections_list.append({'title': content.title(), 'questions': []})
            else:
                if not sections_list:
                    sections_list.append({'title': 'General Procedure', 'questions': []})
                sections_list[-1]['questions'].append(content)
    
    data['sections'] = sections_list
    print(pprint.pformat(data))

if __name__ == '__main__':
    parse_single()
