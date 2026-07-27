import os
import re
import sys
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Requirements for a "Passing" critique document
REQUIRED_HEADERS = ["The Risk", "The Mechanism", "Mitigation Strategies", "Organic Resolution", "Bottom Line"]
KEY_TERMS = ["LVT", "Dividend", "Harberger", "Liability", "Incentive"]

# Advanced Content/Logic Assertions
LOGIC_ASSERTIONS: Dict[str, List[str]] = {
    "01_fiscal_gap.md": ["Zero-Sum", "Subsistence Pivot", "Budget"],
    "02_capital_formation.md": ["Filter", "Mutualist", "Active"],
    "03_insurance_cartel.md": ["Arbitrage", "Collusion", "Neutral Entity"],
    "04_justice_access.md": ["Securitization", "Trust Broker"],
    "05_military_risks.md": ["Bounty", "Logistics Firewall", "Surety Bond"],
    "06_cultural_risks.md": ["Privacy", "Jurisdictional Competition"],
    "08_auditor_capture.md": ["Adversarial", "Bond Forfeiture"],
    "09_dividend_trap.md": ["Risk Offset", "Externality Vault"],
    "10_inter_compact_friction.md": ["Trust Oracle", "Judicial Blockade"],
    "11_litigation_asymmetry.md": ["Sortition", "Redundant"],
    "12_jurisdictional_evasion.md": ["Asset-Linked", "Repo-Market"],
    "13_data_leviathan.md": ["Polycentric", "Actuarial Dissent"],
    "15_class_warfare.md": ["Multi-Compact", "Redistributive", "Exodus"],
    "16_insurer_cascade.md": ["Waterfall", "Parametric", "Retro-Assessment"]
}

def analyze_file(filepath: str) -> bool:
    """Performs a rigorous audit of a systemic critique document."""
    try:
        if not os.path.exists(filepath):
             logging.error(f"File not found: {filepath}")
             return False
             
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().replace('\ufeff', '')
    except Exception as e:
        logging.error(f"Read Error on {os.path.basename(filepath)}: {e}")
        return False
    
    filename = os.path.basename(filepath)
    issues: List[str] = []
    
    # 1. Header Verification (Flexible substring check)
    for req in REQUIRED_HEADERS:
        if req.lower() not in content.lower():
            issues.append(f"Missing section/header: '{req}'")

    # 2. Section Extraction & Depth Check
    start_key = "## Organic Resolution"
    end_key = "## Bottom Line"
    
    start_match = re.search(re.escape(start_key), content, re.IGNORECASE)
    end_match = re.search(re.escape(end_key), content, re.IGNORECASE)
    
    if start_match and end_match:
        start_pos = start_match.end()
        end_pos = end_match.start()
        
        if end_pos > start_pos:
            section_text = content[start_pos:end_pos].strip()
            # Clean text for metrics
            words = re.sub(r'[^a-zA-Z0-9]', ' ', section_text).split()
            word_count = len(words)
            
            if word_count < 40:
                issues.append(f"Resolution too brief ({word_count} words). Need >40.")
                
            # 3. Systemic Keyword Check
            found_key_terms = [t for t in KEY_TERMS if t.lower() in section_text.lower()]
            if not found_key_terms:
                issues.append(f"Lacks core systemic terminology (e.g. LVT, Liability, Dividend).")
                
            # 4. Logical Content Assertions
            if filename in LOGIC_ASSERTIONS:
                missing_logic = [logic for logic in LOGIC_ASSERTIONS[filename] if logic.lower() not in section_text.lower()]
                if missing_logic:
                    issues.append(f"Logic Deficit: Missing implementations for: {missing_logic}")
        else:
            issues.append(f"Markers in wrong order (Start: {start_match.start()}, End: {end_match.start()})")
    else:
        if not start_match: issues.append(f"Missing header: '{start_key}'")
        if not end_match: issues.append(f"Missing header: '{end_key}'")

    if issues:
        logging.warning(f"[FAIL] {filename}")
        for issue in issues:
            logging.warning(f"  - {issue}")
        return False
    else:
        logging.info(f"[PASS] {filename} (Words: {word_count})")
        return True

def main():
    critique_dir = r"/mnt/c/Users/reese/OneDrive/Desktop/AI/The Liability State/4_Critiques_and_Risks"
    logging.info("--- Liability State Final Systemic Audit ---")
    
    all_pass = True
    for filename in sorted(LOGIC_ASSERTIONS.keys()):
        if not analyze_file(os.path.join(critique_dir, filename)):
            all_pass = False
    
    if all_pass:
        logging.info("\nRESULT: SUCCESS - Systemic Integrity Verified.")
        sys.exit(0)
    else:
        logging.error("\nRESULT: FAILURE")
        sys.exit(1)

if __name__ == "__main__":
    main()
