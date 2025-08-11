#!/usr/bin/env python3
"""
Test script to generate slide feedback for document 2
"""
import sys
import os
sys.path.append('backend')

from backend.app.db.database import SessionLocal
from backend.app.services.queue_processor import QueueProcessor
import asyncio

async def test_feedback_generation():
    """Test the slide feedback generation function"""
    print("Testing slide feedback generation for document 2...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create queue processor instance
        processor = QueueProcessor()
        
        # Generate slide feedback for document 2
        result = await processor.generate_slide_feedback(document_id=2, db=db)
        
        if result:
            print("✅ Slide feedback generation completed successfully!")
        else:
            print("❌ Slide feedback generation failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_feedback_generation())