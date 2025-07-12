#!/usr/bin/env python3
"""
Main GPU Processing Script

This script runs on GPU instances to process pitch deck PDFs and generate AI reviews.
It's designed to be executed via the backend orchestration system.
"""

import sys
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List
import logging

# Import the new AI analyzer
from utils.pitch_deck_analyzer import PitchDeckAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """Main PDF processing class for AI analysis"""
    
    def __init__(self, mount_path: str = "/mnt/shared"):
        self.mount_path = mount_path
        self.analyzer = PitchDeckAnalyzer()
        logger.info(f"Initialized PDF processor with mount path: {mount_path}")
        logger.info("AI analyzer initialized successfully")
    
    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Process a PDF file and generate AI-powered review
        
        Args:
            file_path: Path to the PDF file relative to mount_path
            
        Returns:
            Dictionary containing review results
        """
        full_path = os.path.join(self.mount_path, file_path)
        logger.info(f"Processing PDF: {full_path}")
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"PDF file not found: {full_path}")
        
        try:
            # Use real AI processing instead of placeholder
            results = self._ai_processing(full_path)
            logger.info("PDF processing completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    def _ai_processing(self, file_path: str) -> Dict[str, Any]:
        """
        Real AI processing using the PitchDeckAnalyzer
        
        Performs comprehensive analysis including:
        1. Visual analysis of PDF pages using vision models
        2. Detailed analysis across 7 VC evaluation areas
        3. Numerical scoring (0-7) for each area
        4. Scientific hypothesis extraction
        5. Company offering summarization
        """
        logger.info("Running real AI processing...")
        
        try:
            # Use the AI analyzer to process the PDF
            results = self.analyzer.analyze_pdf(file_path)
            
            # Transform results to include additional fields for backward compatibility
            enhanced_results = self._enhance_results_format(results)
            
            logger.info("AI processing completed successfully")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            # Fallback to basic error structure
            return {
                "error": f"AI processing failed: {str(e)}",
                "company_offering": "Error during processing",
                "report_chapters": {},
                "report_scores": {},
                "scientific_hypotheses": "Error during processing",
                "processing_metadata": {
                    "processing_time": 0.0,
                    "error": True
                }
            }
    
    def _enhance_results_format(self, ai_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance AI results with additional fields for compatibility
        
        Adds summary fields and recommendations based on the detailed analysis
        """
        # Calculate overall score from individual area scores
        scores = ai_results.get("report_scores", {})
        if scores:
            overall_score = sum(scores.values()) / len(scores)
        else:
            overall_score = 0.0
        
        # Generate key points from the analysis chapters
        key_points = []
        chapters = ai_results.get("report_chapters", {})
        for area, analysis in chapters.items():
            if analysis and len(analysis) > 10:  # Non-empty analysis
                # Extract first sentence as key point
                first_sentence = analysis.split('.')[0]
                if first_sentence:
                    key_points.append(f"{area.title()}: {first_sentence}")
        
        # Generate recommendations based on low-scoring areas
        recommendations = []
        for area, score in scores.items():
            if score < 4:  # Areas that need improvement
                recommendations.append(f"Strengthen {area.replace('_', ' ')} section with more detailed information")
        
        if not recommendations:
            recommendations = ["Continue developing strong areas identified in the analysis"]
        
        # Enhanced results combining AI analysis with compatibility fields
        enhanced_results = {
            # Core AI analysis results (your structure)
            "company_offering": ai_results.get("company_offering", ""),
            "report_chapters": ai_results.get("report_chapters", {}),
            "report_scores": ai_results.get("report_scores", {}),
            "scientific_hypotheses": ai_results.get("scientific_hypotheses", ""),
            
            # Additional compatibility fields
            "summary": ai_results.get("company_offering", "Comprehensive pitch deck analysis completed"),
            "score": round(overall_score, 1),
            "key_points": key_points[:5],  # Limit to top 5
            "recommendations": recommendations[:4],  # Limit to top 4
            
            # Analysis breakdown for compatibility
            "analysis": {
                "problem_analysis": chapters.get("problem", "")[:200],
                "solution_analysis": chapters.get("solution", "")[:200], 
                "market_fit": chapters.get("product market fit", "")[:200],
                "business_model": chapters.get("monetisation", "")[:200],
                "team_analysis": chapters.get("organisation", "")[:200]
            },
            
            # Metadata
            "processing_metadata": ai_results.get("processing_metadata", {}),
            "confidence_score": min(overall_score / 7.0, 1.0),  # Normalize to 0-1
            "sections_analyzed": list(chapters.keys()),
            "model_version": "ai-v1.0"
        }
        
        return enhanced_results
    
    def save_results(self, results: Dict[str, Any], file_path: str) -> str:
        """Save processing results to shared filesystem"""
        # Create flat filename that matches backend expectation
        flat_filename = file_path.replace('/', '_').replace('.pdf', '_results.json')
        results_path = os.path.join(self.mount_path, 'results', flat_filename)
        
        # Ensure results directory exists
        results_dir = os.path.dirname(results_path)
        os.makedirs(results_dir, exist_ok=True)
        
        # Save results
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to: {results_path}")
        return f"results/{flat_filename}"
    
    def create_completion_marker(self, file_path: str) -> None:
        """Create completion marker for backend monitoring"""
        marker_name = f"processing_complete_{file_path.replace('/', '_')}"
        marker_path = os.path.join(self.mount_path, "temp", marker_name)
        
        # Ensure temp directory exists
        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        
        # Create marker file
        Path(marker_path).touch()
        logger.info(f"Created completion marker: {marker_path}")


def main():
    """Main entry point for GPU processing"""
    if len(sys.argv) != 2:
        print("Usage: python main.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    mount_path = os.environ.get('SHARED_FILESYSTEM_MOUNT_PATH', '/mnt/shared')
    
    try:
        # Initialize processor
        processor = PDFProcessor(mount_path)
        
        # Process PDF
        results = processor.process_pdf(file_path)
        
        # Save results
        results_file = processor.save_results(results, file_path)
        
        # Create completion marker
        processor.create_completion_marker(file_path)
        
        logger.info(f"Processing completed successfully for {file_path}")
        logger.info(f"Results available at: {results_file}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()