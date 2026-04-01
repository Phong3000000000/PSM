import os
import sys
import openpyxl
import json
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Base Paths
# Running inside container, so path is like /mnt/extra-addons/M02.../gdrive_data
# We need to find the specific path. Assume script is run from module root or we find it.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(CURRENT_DIR) # Parent of scripts/
DATA_DIR = os.path.join(MODULE_DIR, 'gdrive_data')
OUTPUT_FILE = os.path.join(MODULE_DIR, 'models', 'soc_initial_data.py')

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found at {DATA_DIR}")
        return

    print(f"Scanning {DATA_DIR}...")
    
    soc_list = []
    
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.xlsx') and not file.startswith('~'):
                full_path = os.path.join(root, file)
                try:
                    soc_data = parse_excel(full_path, DATA_DIR)
                    if soc_data:
                        soc_list.append(soc_data)
                        print(f"Parsed: {soc_data['title']}")
                except Exception as e:
                    print(f"Failed to parse {file}: {e}")

    # Generate Python Code
    write_python_file(soc_list)
    print(f"Successfully wrote {len(soc_list)} SOCs to {OUTPUT_FILE}")

def parse_excel(filepath, base_dir):
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    
    fname = os.path.basename(filepath)
    title = os.path.splitext(fname)[0]
    
    # Heuristics
    rel_path = filepath.replace(base_dir, '').lower()
    
    soc_type = 'bsoc'
    if 'easoc' in rel_path: soc_type = 'asoc'
    
    area = 'kitchen'
    sub_area = 'other'
    
    if 'service' in rel_path: area = 'service'
    elif 'onboarding' in rel_path: area = 'onboarding'
    
    if 'production' in rel_path: sub_area = 'production'
    elif 'mccafe' in rel_path: sub_area = 'mccafe'
    elif 'drive thru' in rel_path or 'drive-thru' in rel_path: sub_area = 'drive_thru'
    elif 'pm task' in rel_path: sub_area = 'pm_task'
    elif 'support' in rel_path: sub_area = 'support'
    elif 'mds' in rel_path: sub_area = 'mds'
    
    # Code Extraction?
    # Simple logic
    code = ""
    
    data = {
        'title': title,
        'code': code,
        'soc_type': soc_type,
        'area': area,
        'sub_area': sub_area,
        'prerequisites': [],
        'sections': []
    }
    
    parsing_mode = None
    
    # Clean helpers
    sections_list = [] # List of {'title': '', 'questions': []}
    
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
             # Skip headers inside prereq blocks if any
            if len(content) > 5 and 'verify' not in content.lower():
                data['prerequisites'].append(content)
                
        elif parsing_mode == 'procedure':
            if content.lower() in ['y', 'n', 'n/a', 'pass', 'fail']: continue
            if len(content) < 3: continue
            
            # Simple Header check
            is_header = False
            if content.lower() in ['chuẩn bị quầy', 'vệ sinh', 'thực hiện', 'service', 'an toàn thực phẩm']:
                is_header = True
                
            # If header, start new section
            if is_header:
                sections_list.append({'title': content.title(), 'questions': []})
            else:
                # Add to last section or create default
                if not sections_list:
                    sections_list.append({'title': 'General Procedure', 'questions': []})
                sections_list[-1]['questions'].append(content)
    
    data['sections'] = sections_list
    return data

def write_python_file(soc_list):
    content = "# -*- coding: utf-8 -*-\n\n"
    content += "def get_initial_soc_data():\n"
    content += "    return [\n"
    
    for soc in soc_list:
        content += "        {\n"
        content += f"            'title': {repr(soc['title'])},\n"
        content += f"            'code': {repr(soc['code'])},\n"
        content += f"            'soc_type': {repr(soc['soc_type'])},\n"
        content += f"            'area': {repr(soc['area'])},\n"
        content += f"            'sub_area': {repr(soc['sub_area'])},\n"
        content += f"            'prerequisites': {repr(soc['prerequisites'])},\n"
        content += "            'sections': [\n"
        for section in soc['sections']:
            content += "                {\n"
            content += f"                    'title': {repr(section['title'])},\n"
            content += f"                    'questions': {repr(section['questions'])}\n"
            content += "                },\n"
        content += "            ]\n"
        content += "        },\n"
    
    content += "    ]\n"
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    main()
