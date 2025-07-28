#!/usr/bin/env python3
"""
Healthcare Sectors Database Debug Script
Check what healthcare sectors and keywords are actually stored in the database
"""

import sys
import json
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_healthcare_sectors():
    """Check what healthcare sectors are in the database"""
    print("🏥 Healthcare Sectors Database Analysis")
    print("=" * 60)
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # First, check if the table exists
        try:
            table_exists = db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'healthcare_sectors'
                )
            """)).fetchone()[0]
            
            print(f"healthcare_sectors table exists: {'✅ Yes' if table_exists else '❌ No'}")
            
        except Exception as e:
            print(f"❌ Error checking table existence: {e}")
            table_exists = False
        
        if not table_exists:
            print("\n🔄 Since healthcare_sectors table doesn't exist, showing fallback sectors from code:")
            show_fallback_sectors()
            return
            
        # Get all healthcare sectors
        try:
            sectors = db.execute(text("""
                SELECT id, name, display_name, description, keywords, subcategories, 
                       confidence_threshold, regulatory_requirements, is_active
                FROM healthcare_sectors
                ORDER BY id
            """)).fetchall()
            
            print(f"\n📊 Found {len(sectors)} healthcare sectors in database:")
            print("-" * 60)
            
            for sector in sectors:
                sector_id, name, display_name, description, keywords_json, subcategories_json, confidence_threshold, regulatory_json, is_active = sector
                
                print(f"\n🏷️  Sector ID: {sector_id}")
                print(f"   Name: {name}")
                print(f"   Display Name: {display_name}")
                print(f"   Active: {'✅' if is_active else '❌'}")
                print(f"   Description: {description}")
                print(f"   Confidence Threshold: {confidence_threshold}")
                
                # Parse keywords
                try:
                    keywords = json.loads(keywords_json) if keywords_json else []
                    print(f"   Keywords ({len(keywords)}): {', '.join(keywords[:10])}{'...' if len(keywords) > 10 else ''}")
                    if len(keywords) > 10:
                        print(f"   Full Keywords: {keywords}")
                except json.JSONDecodeError:
                    print(f"   Keywords (raw): {keywords_json}")
                
                # Parse subcategories  
                try:
                    subcategories = json.loads(subcategories_json) if subcategories_json else []
                    print(f"   Subcategories: {', '.join(subcategories)}")
                except json.JSONDecodeError:
                    print(f"   Subcategories (raw): {subcategories_json}")
                
                # Parse regulatory requirements
                try:
                    regulatory = json.loads(regulatory_json) if regulatory_json else []
                    print(f"   Regulatory: {', '.join(regulatory)}")
                except json.JSONDecodeError:
                    print(f"   Regulatory (raw): {regulatory_json}")
                    
        except Exception as e:
            print(f"❌ Error querying healthcare_sectors: {e}")
            print("\n🔄 Showing fallback sectors from code:")
            show_fallback_sectors()
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("\n🔄 Showing fallback sectors from code:")
        show_fallback_sectors()

def show_fallback_sectors():
    """Show the hardcoded fallback sectors from the code"""
    fallback_sectors = [
        {
            "id": 1,
            "name": "healthtech",
            "display_name": "HealthTech",
            "description": "General health technology solutions",
            "keywords": ["health", "medical", "healthcare", "digital health", "telemedicine", "ai", "artificial intelligence", "medical imaging", "diagnostics"],
            "subcategories": ["Digital Health", "Telemedicine", "Health Apps"],
            "confidence_threshold": 0.3,
            "regulatory_requirements": []
        },
        {
            "id": 2,
            "name": "medtech",
            "display_name": "MedTech", 
            "description": "Medical devices and equipment",
            "keywords": ["device", "medical device", "equipment", "surgical", "implant", "monitoring"],
            "subcategories": ["Medical Devices", "Surgical Equipment"],
            "confidence_threshold": 0.3,
            "regulatory_requirements": []
        }
    ]
    
    print(f"📋 Fallback Sectors ({len(fallback_sectors)} sectors):")
    print("-" * 60)
    
    for sector in fallback_sectors:
        print(f"\n🏷️  {sector['display_name']} ({sector['name']})")
        print(f"   Description: {sector['description']}")
        print(f"   Keywords: {', '.join(sector['keywords'])}")
        print(f"   Subcategories: {', '.join(sector['subcategories'])}")
        print(f"   Confidence Threshold: {sector['confidence_threshold']}")

def test_classifier_initialization():
    """Test what the StartupClassifier actually loads"""
    print("\n" + "=" * 60)
    print("🤖 StartupClassifier Initialization Test")
    print("=" * 60)
    
    try:
        from app.db.database import get_db
        from app.services.startup_classifier import StartupClassifier
        
        db = next(get_db())
        classifier = StartupClassifier(db)
        
        print(f"✅ StartupClassifier initialized successfully")
        print(f"📊 Loaded {len(classifier.sectors)} sectors")
        print(f"🤖 Using model: {classifier.classification_model}")
        
        print(f"\n🏷️  Actually loaded sectors:")
        for i, sector in enumerate(classifier.sectors):
            print(f"   {i+1}. {sector['display_name']} ({sector['name']})")
            print(f"      Keywords: {', '.join(sector['keywords'][:5])}{'...' if len(sector['keywords']) > 5 else ''}")
            
    except Exception as e:
        print(f"❌ StartupClassifier initialization failed: {e}")
        import traceback
        traceback.print_exc()

def check_model_configs():
    """Check what models are configured in the database"""
    print("\n" + "=" * 60) 
    print("🔧 Model Configuration Check")
    print("=" * 60)
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Check if model_configs table exists
        try:
            table_exists = db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'model_configs'
                )
            """)).fetchone()[0]
            
            print(f"model_configs table exists: {'✅ Yes' if table_exists else '❌ No'}")
            
            if table_exists:
                models = db.execute(text("""
                    SELECT model_name, model_type, is_active 
                    FROM model_configs
                    ORDER BY model_type, model_name
                """)).fetchall()
                
                print(f"📋 Found {len(models)} model configurations:")
                for model_name, model_type, is_active in models:
                    status = "✅ Active" if is_active else "❌ Inactive"
                    print(f"   {model_name} ({model_type}) - {status}")
            else:
                print("🔄 Using fallback model: gemma3:12b")
                
        except Exception as e:
            print(f"❌ Error checking model configs: {e}")
            print("🔄 Using fallback model: gemma3:12b")
            
    except Exception as e:
        print(f"❌ Database connection error for model configs: {e}")

def main():
    """Main function"""
    check_healthcare_sectors()
    test_classifier_initialization() 
    check_model_configs()
    
    print("\n" + "=" * 60)
    print("🎯 Summary:")
    print("   - If healthcare_sectors table doesn't exist, only 2 fallback sectors are used")
    print("   - If you expected 8 sectors, they need to be inserted into the database")
    print("   - The classifier uses whatever sectors are actually loaded (DB or fallback)")
    print("=" * 60)

if __name__ == "__main__":
    main()