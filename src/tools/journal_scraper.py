import pandas as pd
import json
import math
from collections import OrderedDict
import time

# SJR category IDs (biomedical/medical):
# 1207=History and Philosophy of Science, 2204=Biomedical Engineering, 1306=Cancer Research, 1308=Clinical Biochemistry, 1309=Developmental Biology, 1313=Molecular Medicine, 2403=Immunology, 2404=Microbiology, 2406=Virology, 2502=Biomaterials, 2700=General Medicine, 2701=Medicine (misc), 2704=Biochemistry (medical), 2705=Cardiology, 2706=Critical Care, 2712=Endocrinology, 2713=Epidemiology, 2716=Genetics (clinical), 2720=Hematology, 2725=Infectious Diseases, 2728=Neurology (clinical), 2730=Oncology, 2735=Pediatrics, 2736=Pharmacology (medical), 2737=Physiology (medical), 2738=Psychiatry, 2739=Public Health, 2746=Surgery, 2800=Neuroscience, 3002=Drug Discovery, 3003=Pharmaceutical Science, 3004=Pharmacology, 3005=Toxicology
category_ids = [
    1207, 2204, 1306, 1308, 1309, 1313, 2403, 2404, 2406, 2502, 2700, 2701, 2704, 2705, 2706, 2712, 2713, 2716, 2720, 2725, 2728, 2730, 2735, 2736, 2737, 2738, 2739, 2746, 2800, 3002, 3003, 3004, 3005
]

journal_data = {}

print(f"Starting to process {len(category_ids)} biomedical categories...")

for i, category_id in enumerate(category_ids, 1):
    url = f"https://www.scimagojr.com/journalrank.php?category={category_id}&out=xls"
    
    print(f"[{i:2d}/{len(category_ids)}] Processing category {category_id}...", end=" ")
    
    try:
        df = pd.read_csv(url, sep=';', encoding='utf-8')
        
        journals_in_category = len(df)
        print(f"({journals_in_category} journals)")
        
        for _, row in df.iterrows():
            # Extract journal name 
            name = str(row['Title']).strip().strip('"')
            
            # Parse SJR 
            sjr_raw = str(row['SJR']).replace(',', '.')
            try:
                sjr = float(sjr_raw)
            except (ValueError, TypeError):
                print(f"    Skipping {name} - invalid SJR: {sjr_raw}")
                continue
            
            # Parse ISSN field (can contain multiple ISSNs separated by commas)
            issn_raw = str(row['Issn']) if 'Issn' in df.columns else ''
            
            if pd.notna(row.get('Issn')) and issn_raw != 'nan':
                # Split by comma 
                issns = [issn.strip().strip('"') for issn in issn_raw.split(',') if issn.strip()]
                electronic_issn = issns[0] if len(issns) > 0 else None
                print_issn = issns[1] if len(issns) > 1 else None
            else:
                print_issn = None
                electronic_issn = None
            
            # Extract additional metadata
            quartile = str(row.get('SJR Quartile', '')).strip()
            h_index = row.get('H index', '')
            country = str(row.get('Country', '')).strip().strip('"')
            publisher = str(row.get('Publisher', '')).strip().strip('"')
            categories = str(row.get('Categories', '')).strip().strip('"')
            
            # Create complete journal entry
            journal_entry = {
                'sjr': sjr,
                'print_issn': print_issn,
                'electronic_issn': electronic_issn,
                'quartile': quartile,
                'h_index': h_index,
                'country': country,
                'publisher': publisher,
                'categories': categories
            }
            
            # Handle duplicates
            if name in journal_data:
                if sjr > journal_data[name]['sjr']:
                    journal_data[name] = journal_entry
                    print(f"    Updated {name} with higher SJR: {sjr}")
            else:
                journal_data[name] = journal_entry
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f"FAILED - {e}")
        continue

# Filter out NaN values FIRST
print(f"\nFiltering out journals with NaN SJR values...")
clean_data = {name: data for name, data in journal_data.items() 
              if str(data['sjr']).lower() != 'nan'}

print(f"Removed {len(journal_data) - len(clean_data)} journals with NaN SJR")

# Sort journals by SJR 
print(f"Sorting {len(clean_data)} unique journals by SJR score...")
sorted_journals = OrderedDict(
    sorted(clean_data.items(), key=lambda x: x[1]['sjr'], reverse=True)
)

# Save to JSON file
output_path = 'biomedical_journals.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(sorted_journals, f, indent=2, ensure_ascii=False)

print(f"\nSuccessfully saved {len(sorted_journals)} unique journals to {output_path}")