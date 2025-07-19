import pandas as pd
import json
from collections import OrderedDict

# SJR category IDs (biomedical/medical):
# 1000=Multidisciplinary, 2204=Biomedical Engineering, 1306=Cancer Research, 1308=Clinical Biochemistry, 1309=Developmental Biology, 1313=Molecular Medicine, 2403=Immunology, 2404=Microbiology, 2406=Virology, 2502=Biomaterials, 2700=General Medicine, 2701=Medicine (misc), 2704=Biochemistry (medical), 2705=Cardiology, 2706=Critical Care, 2712=Endocrinology, 2713=Epidemiology, 2716=Genetics (clinical), 2720=Hematology, 2725=Infectious Diseases, 2728=Neurology (clinical), 2730=Oncology, 2735=Pediatrics, 2736=Pharmacology (medical), 2737=Physiology (medical), 2738=Psychiatry, 2739=Public Health, 2746=Surgery, 2800=Neuroscience, 3002=Drug Discovery, 3003=Pharmaceutical Science, 3004=Pharmacology, 3005=Toxicology
category_ids = [
    1000, 2204, 1306, 1308, 1309, 1313, 2403, 2404, 2406, 2502, 2700, 2701, 2704, 2705, 2706, 2712, 2713, 2716, 2720, 2725, 2728, 2730, 2735, 2736, 2737, 2738, 2739, 2746, 2800, 3002, 3003, 3004, 3005
]

journal_impact = {}

for category_id in category_ids:
    url = f"https://www.scimagojr.com/journalrank.php?category={category_id}"
    try:
        df = pd.read_html(url)[0]
    except Exception as e:
        print(f"Failed to read category {category_id}: {e}")
        continue
    journal_col = 'Title' if 'Title' in df.columns else df.columns[1]
    impact_col = 'SJR' if 'SJR' in df.columns else df.columns[-2]
    for _, row in df.iterrows():
        name = str(row[journal_col]).strip()
        sjr_raw = str(row[impact_col])
        sjr_num = sjr_raw.split()[0].replace(',', '').strip() if sjr_raw else ''
        try:
            sjr = float(sjr_num)
        except Exception:
            continue
        if name in journal_impact:
            journal_impact[name] = max(journal_impact[name], sjr)
        else:
            journal_impact[name] = sjr

sorted_journals = OrderedDict(sorted(journal_impact.items(), key=lambda x: x[1], reverse=True))

output_path = 'biomedical_journals.json'
with open(output_path, 'w') as f:
    json.dump(sorted_journals, f, indent=2)

print(f"Saved {len(sorted_journals)} unique journals to {output_path}")
