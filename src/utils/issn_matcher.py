import json
import re
import os
from typing import Dict, Optional, List

def find_journal_json_path() -> str:
    """Find the biomedical_journals.json file path."""
    # First check current directory
    if os.path.exists("biomedical_journals.json"):
        return "biomedical_journals.json"
    
    # Check project root (where journal_scraper.py outputs it)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    root_path = os.path.join(project_root, "biomedical_journals.json")
    if os.path.exists(root_path):
        return root_path
    
    raise FileNotFoundError("biomedical_journals.json not found")

def load_journal_data(json_path: str = None) -> Dict:
    """Load journal data from JSON file."""
    if json_path is None:
        json_path = find_journal_json_path()
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_issn(issn: str) -> str:
    """Normalize ISSN by removing hyphens and spaces."""
    if not issn or issn in ["N/A", "unpublished"]:
        return ""
    return re.sub(r'[-\s]', '', str(issn).strip())

def find_journal_by_issn(issn: str, journal_data: Dict) -> Optional[Dict]:
    """Find journal entry by ISSN (checks both print and electronic)."""
    normalized_issn = normalize_issn(issn)
    if not normalized_issn:
        return None
    
    for journal_name, data in journal_data.items():
        print_issn = normalize_issn(data.get('print_issn', ''))
        electronic_issn = normalize_issn(data.get('electronic_issn', ''))
        
        if normalized_issn in [print_issn, electronic_issn]:
            return {
                'journal_name': journal_name,
                'matched_issn': issn,
                'journal_data': data
            }
    return None

def match_medrxiv_result(medrxiv_result: Dict, journal_data: Dict) -> Dict:
    """Match a medrxiv result with journal database and assess credibility."""
    issn = medrxiv_result.get('issn')
    base_result = {
        'source': 'medrxiv',
        'paper_title': medrxiv_result.get('title'),
        'paper_issn': issn,
    }
    
    if not issn or issn == "unpublished":
        return {
            **base_result,
            'credibility_status': 'unverified',
            'credibility_reason': 'Preprint not yet published in peer-reviewed journal',
            'journal_match': False
        }
    
    match = find_journal_by_issn(issn, journal_data)
    if match:
        return {
            **base_result,
            'credibility_status': 'verified',
            'credibility_reason': f"Published in {match['journal_name']} (SJR: {match['journal_data']['sjr']})",
            'journal_match': True,
            **match
        }
    else:
        return {
            **base_result,
            'credibility_status': 'unverified',
            'credibility_reason': 'Journal not found in curated biomedical database',
            'journal_match': False
        }

def match_litesense_result(litesense_text: str, journal_data: Dict) -> Dict:
    """Extract ISSNs from litesense formatted text and assess credibility."""
    # Extract e-ISSN and p-ISSN from the formatted text
    e_issn_match = re.search(r'e-ISSN: ([^,\]]+)', litesense_text)
    p_issn_match = re.search(r'p-ISSN: ([^,\]]+)', litesense_text)
    
    base_result = {
        'source': 'litesense',
        'paper_text': litesense_text.split('\n')[0][:100] + "...",
    }
    
    # Check both ISSNs for matches
    issns_to_check = []
    if e_issn_match:
        issns_to_check.append((e_issn_match.group(1).strip(), 'e-ISSN'))
    if p_issn_match:
        issns_to_check.append((p_issn_match.group(1).strip(), 'p-ISSN'))
    
    if not issns_to_check:
        return {
            **base_result,
            'credibility_status': 'unverified',
            'credibility_reason': 'No ISSN found in result',
            'journal_match': False
        }
    
    # Check for matches (prioritize any successful match)
    for issn, issn_type in issns_to_check:
        if issn in ["N/A", "n/a"]:
            continue
            
        match = find_journal_by_issn(issn, journal_data)
        if match:
            return {
                **base_result,
                'paper_issn': issn,
                'issn_type': issn_type,
                'credibility_status': 'verified',
                'credibility_reason': f"Published in {match['journal_name']} (SJR: {match['journal_data']['sjr']})",
                'journal_match': True,
                **match
            }
    
    # No matches found for any ISSN
    issn_list = [issn for issn, _ in issns_to_check if issn not in ["N/A", "n/a"]]
    return {
        **base_result,
        'paper_issn': ', '.join(issn_list),
        'credibility_status': 'unverified',
        'credibility_reason': 'Journal not found in curated biomedical database',
        'journal_match': False
    }

def check_issn_matches(medrxiv_results: List[Dict] = None, litesense_results: List[str] = None, 
                      journal_json_path: str = None) -> Dict:
    """Check ISSN matches and assess credibility for both medrxiv and litesense results."""
    journal_data = load_journal_data(journal_json_path)
    results = {
        'medrxiv_results': [],
        'litesense_results': [],
        'summary': {
            'medrxiv': {'verified': 0, 'unverified': 0},
            'litesense': {'verified': 0, 'unverified': 0}
        }
    }
    
    if medrxiv_results:
        for result in medrxiv_results:
            assessment = match_medrxiv_result(result, journal_data)
            results['medrxiv_results'].append(assessment)
            results['summary']['medrxiv'][assessment['credibility_status']] += 1
    
    if litesense_results:
        for result in litesense_results:
            assessment = match_litesense_result(result, journal_data)
            results['litesense_results'].append(assessment)
            results['summary']['litesense'][assessment['credibility_status']] += 1
    
    return results