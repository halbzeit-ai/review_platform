#!/usr/bin/env python3
"""
Test Classification Prompt Generation
Prove that all 8 sectors are being used in the actual classification prompt
"""

import sys
import asyncio
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

async def test_classification_prompt():
    """Test the actual prompt generation with a sample company offering"""
    try:
        from app.db.database import get_db
        from app.services.startup_classifier import StartupClassifier
        
        db = next(get_db())
        classifier = StartupClassifier(db)
        
        print("🧪 Testing Classification Prompt Generation")
        print("=" * 70)
        
        # Sample company offering
        test_offering = "We provide AI-driven medical imaging analysis to help radiologists detect early stage cancer using machine learning algorithms"
        
        print(f"📝 Test Company Offering:")
        print(f"   {test_offering}")
        print()
        
        print(f"📊 Classifier loaded {len(classifier.sectors)} sectors:")
        for i, sector in enumerate(classifier.sectors, 1):
            print(f"   {i}. {sector['display_name']} ({sector['name']})")
        print()
        
        # Step 1: Test keyword-based classification
        top_candidates = classifier._keyword_based_classification(test_offering)
        print(f"🔍 Keyword-based top candidates ({len(top_candidates)}):")
        for i, candidate in enumerate(top_candidates, 1):
            sector = candidate["sector"]
            print(f"   {i}. {sector['display_name']} (score: {candidate['score']:.3f})")
            print(f"      Matched keywords: {', '.join(candidate['matched_keywords'])}")
        print()
        
        # Step 2: Generate the actual prompt
        prompt = classifier._create_classification_prompt(test_offering, top_candidates)
        
        print("📋 GENERATED CLASSIFICATION PROMPT:")
        print("=" * 70)
        print(prompt)
        print("=" * 70)
        
        # Parse the prompt to count sectors mentioned
        lines = prompt.split('\n')
        sector_lines = []
        in_sectors_section = False
        
        for line in lines:
            if "Healthcare Sectors:" in line:
                in_sectors_section = True
                continue
            elif in_sectors_section:
                if line.startswith("Top Candidate Sectors"):
                    break
                if line.strip().startswith("- "):
                    sector_lines.append(line.strip())
        
        print(f"🎯 PROOF - Sectors in prompt: {len(sector_lines)}")
        for i, sector_line in enumerate(sector_lines, 1):
            print(f"   {i}. {sector_line}")
        
        if len(sector_lines) == 8:
            print("\n✅ CONFIRMED: All 8 sectors are included in the classification prompt")
        else:
            print(f"\n❌ ISSUE: Only {len(sector_lines)} sectors found in prompt, expected 8")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_classification_prompt())