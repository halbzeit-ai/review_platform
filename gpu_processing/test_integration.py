#!/usr/bin/env python3
"""
Integration Test Script
Tests the complete AI processing pipeline without requiring actual Ollama models
"""

import sys
import json
import os
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.append('.')

from main import PDFProcessor
from utils.pitch_deck_analyzer import PitchDeckAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_analyzer_initialization():
    """Test that the analyzer can be initialized"""
    try:
        analyzer = PitchDeckAnalyzer()
        logger.info("✓ PitchDeckAnalyzer initialization successful")
        
        # Check if all required attributes exist
        required_attrs = ['llm_model', 'report_model', 'score_model', 'analysis_areas', 'prompts']
        for attr in required_attrs:
            if hasattr(analyzer, attr):
                logger.info(f"  ✓ {attr}: {getattr(analyzer, attr) if attr != 'prompts' else 'Present'}")
            else:
                logger.error(f"  ✗ Missing attribute: {attr}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"✗ Analyzer initialization failed: {e}")
        return False

def test_processor_initialization():
    """Test that the main processor can be initialized"""
    try:
        processor = PDFProcessor("/tmp/test_mount")
        logger.info("✓ PDFProcessor initialization successful")
        
        # Check if analyzer is properly integrated
        if hasattr(processor, 'analyzer'):
            logger.info("  ✓ AI analyzer properly integrated")
            return True
        else:
            logger.error("  ✗ AI analyzer not integrated")
            return False
            
    except Exception as e:
        logger.error(f"✗ Processor initialization failed: {e}")
        return False

def test_results_format():
    """Test that the results format structure is correct"""
    try:
        processor = PDFProcessor("/tmp/test_mount")
        
        # Test with mock AI results
        mock_ai_results = {
            "company_offering": "Test offering description",
            "report_chapters": {
                "problem": "Test problem analysis",
                "solution": "Test solution analysis",
                "product market fit": "Test PMF analysis",
                "monetisation": "Test monetization analysis",
                "financials": "Test financial analysis",
                "use of funds": "Test use of funds analysis",
                "organisation": "Test organization analysis"
            },
            "report_scores": {
                "problem": 5,
                "solution": 6,
                "product market fit": 3,
                "monetisation": 4,
                "financials": 2,
                "use of funds": 4,
                "organisation": 5
            },
            "scientific_hypotheses": "1. Test hypothesis\n2. Another hypothesis",
            "processing_metadata": {
                "processing_time": 120.0,
                "model_versions": {
                    "vision_model": "gemma3:12b",
                    "report_model": "gemma3:12b",
                    "score_model": "phi4:latest"
                }
            }
        }
        
        # Test the enhancement method
        enhanced_results = processor._enhance_results_format(mock_ai_results)
        
        # Check required fields
        required_fields = [
            "company_offering", "report_chapters", "report_scores", 
            "scientific_hypotheses", "summary", "score", "key_points", 
            "recommendations", "analysis", "processing_metadata"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in enhanced_results:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"✗ Missing fields in results: {missing_fields}")
            return False
        
        logger.info("✓ Results format validation successful")
        logger.info(f"  - Overall score: {enhanced_results['score']}")
        logger.info(f"  - Key points count: {len(enhanced_results['key_points'])}")
        logger.info(f"  - Recommendations count: {len(enhanced_results['recommendations'])}")
        logger.info(f"  - Analysis areas: {len(enhanced_results['analysis'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Results format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_operations():
    """Test file operation methods"""
    try:
        processor = PDFProcessor("/tmp/test_mount")
        
        # Create test directories
        os.makedirs("/tmp/test_mount/results", exist_ok=True)
        os.makedirs("/tmp/test_mount/temp", exist_ok=True)
        
        # Test results saving
        test_results = {"test": "data", "score": 5.5}
        results_file = processor.save_results(test_results, "uploads/test_deck.pdf")
        
        # Check if file was created
        expected_file = "/tmp/test_mount/results/uploads_test_deck_results.json"
        if os.path.exists(expected_file):
            logger.info("✓ Results file saving successful")
            
            # Verify content
            with open(expected_file, 'r') as f:
                saved_data = json.load(f)
            if saved_data == test_results:
                logger.info("  ✓ Results content correct")
            else:
                logger.error("  ✗ Results content mismatch")
                return False
        else:
            logger.error(f"✗ Results file not created: {expected_file}")
            return False
        
        # Test completion marker
        processor.create_completion_marker("uploads/test_deck.pdf")
        marker_file = "/tmp/test_mount/temp/processing_complete_uploads_test_deck.pdf"
        if os.path.exists(marker_file):
            logger.info("✓ Completion marker creation successful")
        else:
            logger.error(f"✗ Completion marker not created: {marker_file}")
            return False
        
        # Cleanup
        os.remove(expected_file)
        os.remove(marker_file)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ File operations test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    logger.info("=== AI Integration Test Suite ===")
    
    tests = [
        ("Analyzer Initialization", test_analyzer_initialization),
        ("Processor Initialization", test_processor_initialization),
        ("Results Format", test_results_format),
        ("File Operations", test_file_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing: {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"Test failed: {test_name}")
    
    logger.info(f"\n=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        logger.info("🎉 All integration tests passed!")
        logger.info("The AI processing pipeline is ready for deployment.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)