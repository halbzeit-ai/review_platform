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
import requests
from pathlib import Path
from typing import Dict, Any, List
import logging

# Import the new healthcare template analyzer
from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """Main PDF processing class for AI analysis"""
    
    def __init__(self, mount_path: str = "/mnt/shared", backend_url: str = "http://localhost:8000"):
        self.mount_path = mount_path
        self.backend_url = backend_url
        self.analyzer = HealthcareTemplateAnalyzer(backend_base_url=backend_url)
        logger.info(f"Initialized PDF processor with mount path: {mount_path}")
        logger.info(f"Healthcare template analyzer initialized with backend URL: {backend_url}")
        logger.info("AI analyzer initialized successfully")
    
    # OLD MONOLITHIC METHOD REMOVED - Now using 4 separate methods:
    # process_visual_analysis(), process_slide_feedback(), 
    # process_extractions_and_template(), process_specialized_analysis()
    def process_extractions_and_template(self, file_path: str, company_id: str = None, deck_id: int = None) -> Dict[str, Any]:
        """
        Text Container AI processing using the HealthcareTemplateAnalyzer
        
        Performs text-based healthcare analysis including:
        1. Company offering extraction and healthcare sector classification (from vision cache)
        2. Template-based analysis with healthcare-specific questions
        3. Question-level scoring with healthcare criteria
        
        Vision Container tasks (handled separately):
        - Visual analysis of PDF pages using vision models
        - Slide feedback generation
        
        Specialized analysis tasks (handled separately):
        - Clinical validation, regulatory, scientific analyses
        """
        logger.info(f"Running text container healthcare analysis... (deck_id: {deck_id})")
        current_stage = "initialization"
        
        try:
            current_stage = "text_processing_extractions_and_template"
            logger.info(f"🔍 Starting stage: {current_stage}")
            
            # Use the healthcare template analyzer for text processing only
            # Visual analysis results will be retrieved from cache by the analyzer
            results = self.analyzer.analyze_pdf(file_path, company_id, deck_id=deck_id)
            
            current_stage = "results_enhancement"
            logger.info(f"🔍 Starting stage: {current_stage}")
            
            # Transform results to include additional fields for backward compatibility
            enhanced_results = self._enhance_healthcare_results_format(results)
            
            logger.info("Healthcare template analysis completed successfully")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Healthcare template analysis failed at stage '{current_stage}': {e}")
            # Enhanced error structure with stage information
            return {
                "success": False,
                "error": f"Healthcare template analysis failed at stage '{current_stage}': {str(e)}",
                "failed_stage": current_stage,
                "company_offering": "Error during processing",
                "classification": None,
                "chapter_analysis": {},
                "question_analysis": {},
                "specialized_analysis": {},
                "overall_score": 0.0,
                "processing_metadata": {
                    "processing_time": 0.0,
                    "error": True,
                    "failed_stage": current_stage,
                    "failure_reason": str(e)
                }
            }
    
    def _enhance_healthcare_results_format(self, ai_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance healthcare template results with additional fields for compatibility
        
        Transforms new healthcare template results to maintain backward compatibility
        while adding new healthcare-specific fields
        """
        # Extract healthcare-specific results
        overall_score = ai_results.get("overall_score", 0.0)
        chapter_analysis = ai_results.get("chapter_analysis", {})
        question_analysis = ai_results.get("question_analysis", {})
        classification = ai_results.get("classification", {})
        specialized_analysis = ai_results.get("specialized_analysis", {})
        
        # Generate key points from chapter analysis
        key_points = []
        for chapter_id, chapter_data in chapter_analysis.items():
            chapter_name = chapter_data.get("name", chapter_id)
            if chapter_data.get("responses"):
                # Extract first meaningful response
                first_response = chapter_data["responses"][0] if chapter_data["responses"] else ""
                if first_response and len(first_response) > 10:
                    first_sentence = first_response.split('.')[0]
                    if first_sentence:
                        key_points.append(f"{chapter_name}: {first_sentence}")
        
        # Generate recommendations based on low-scoring chapters
        recommendations = []
        for chapter_id, chapter_data in chapter_analysis.items():
            chapter_name = chapter_data.get("name", chapter_id)
            weighted_score = chapter_data.get("weighted_score", 0.0)
            if weighted_score < 4:  # Areas that need improvement
                recommendations.append(f"Strengthen {chapter_name} with more detailed information")
        
        if not recommendations:
            recommendations = ["Continue developing strong areas identified in the analysis"]
        
        # Create report structure using new questions format
        report_chapters = {}
        report_scores = {}
        
        for chapter_id, chapter_data in chapter_analysis.items():
            # Use the new structured question data
            chapter_questions = chapter_data.get("questions", [])
            
            if chapter_questions:
                # Create formatted chapter content using structured question data
                formatted_content = []
                for question_data in chapter_questions:
                    question_text = question_data.get("question_text", "")
                    response = question_data.get("response", "")
                    score = question_data.get("score", 0)
                    
                    if response and response.strip():
                        # Format each question as a clear section with bold headings
                        formatted_content.append(f"**{question_text}**\n\n{response.strip()}\n\n**Score: {score}/7**")
                
                # Join all questions with section separators for proper formatting
                if formatted_content:
                    report_chapters[chapter_id] = "\n\n---\n\n".join(formatted_content)
                else:
                    report_chapters[chapter_id] = "No question responses available for this chapter."
            else:
                # Error case - no structured questions found
                report_chapters[chapter_id] = "ERROR: No structured questions found in chapter analysis."
            
            report_scores[chapter_id] = chapter_data.get("weighted_score", 0.0)
        
        # Enhanced results combining new healthcare analysis with backward compatibility
        enhanced_results = {
            # CRITICAL: Success field for queue system completion
            "success": True,
            
            # Core healthcare template results (new structure)
            "company_offering": ai_results.get("company_offering", ""),
            "classification": classification,
            "template_used": ai_results.get("template_used"),
            "chapter_analysis": chapter_analysis,
            "question_analysis": question_analysis,
            "specialized_analysis": specialized_analysis,
            "overall_score": overall_score,
            
            # Backward compatibility fields (old structure)
            "report_chapters": report_chapters,
            "report_scores": report_scores,
            "scientific_hypotheses": specialized_analysis.get("scientific_hypothesis", ""),
            
            # Additional compatibility fields
            "summary": ai_results.get("company_offering", "Healthcare startup analysis completed"),
            "score": round(overall_score, 1),
            "key_points": key_points[:5],  # Limit to top 5
            "recommendations": recommendations[:4],  # Limit to top 4
            
            # Analysis breakdown for compatibility
            "analysis": {
                "problem_analysis": report_chapters.get("problem_analysis", "")[:200],
                "solution_analysis": report_chapters.get("solution_approach", "")[:200], 
                "market_fit": report_chapters.get("product_market_fit", "")[:200],
                "business_model": report_chapters.get("monetisation", "")[:200],
                "team_analysis": report_chapters.get("organisation", "")[:200]
            },
            
            # Healthcare-specific metadata
            "processing_metadata": ai_results.get("processing_metadata", {}),
            "confidence_score": min(overall_score / 7.0, 1.0),  # Normalize to 0-1
            "sections_analyzed": list(chapter_analysis.keys()),
            "model_version": "healthcare-template-v1.0",
            "healthcare_sector": classification.get("primary_sector") if classification else None,
            "classification_confidence": classification.get("confidence_score") if classification else None,
            
            # Critical field for deck viewer - visual analysis results
            "visual_analysis_results": ai_results.get("visual_analysis_results", [])
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
    
    def save_specialized_analysis(self, document_id: int, specialized_analysis: Dict[str, Any]) -> bool:
        """Save specialized analysis results to backend database"""
        try:
            # Filter out empty or None values
            filtered_analysis = {
                key: value for key, value in specialized_analysis.items() 
                if value and str(value).strip()
            }
            
            if not filtered_analysis:
                logger.info(f"No specialized analysis to save for deck {document_id}")
                return True
            
            endpoint = f"{self.backend_url}/api/internal/save-specialized-analysis"
            payload = {
                "document_id": document_id,
                "specialized_analysis": filtered_analysis
            }
            
            logger.info(f"💾 Saving specialized analysis to backend: {list(filtered_analysis.keys())}")
            
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Specialized analysis saved successfully: {result.get('saved_analyses', [])}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving specialized analysis for deck {document_id}: {e}")
            return False

    def process_specialized_analysis(self, document_id: int, analysis_type: str) -> bool:
        """Process specialized analysis for a specific document and analysis type as a separate task"""
        try:
            logger.info(f"🔬 Processing {analysis_type} specialized analysis for document {document_id}")
            
            # Get visual analysis results from cache to feed into specialized analysis
            visual_analysis_results = self._get_cached_visual_analysis(document_id)
            if not visual_analysis_results:
                logger.error(f"❌ No cached visual analysis found for document {document_id}. Cannot run specialized analysis.")
                return False
            
            # Run the specialized analysis using the existing healthcare template analyzer method
            logger.info(f"🔍 Running specialized analysis with {len(visual_analysis_results)} pages of visual data")
            specialized_results = self.analyzer.run_specialized_analysis_only(
                visual_analysis_results=visual_analysis_results
            )
            
            # Filter results to only include the requested analysis type
            filtered_results = {}
            if analysis_type in specialized_results:
                filtered_results[analysis_type] = specialized_results[analysis_type]
                logger.info(f"✅ Generated {analysis_type} specialized analysis")
            else:
                logger.warning(f"⚠️ Requested analysis type '{analysis_type}' not found in results: {list(specialized_results.keys())}")
                # Still save what we got - the analyzer determines which analyses to run
                filtered_results = specialized_results
            
            # Save the specialized analysis results to the backend
            if filtered_results:
                success = self.save_specialized_analysis(document_id, filtered_results)
                if success:
                    logger.info(f"✅ {analysis_type} specialized analysis completed and saved for document {document_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to save {analysis_type} specialized analysis for document {document_id}")
                    return False
            else:
                logger.warning(f"⚠️ No {analysis_type} specialized analysis results to save for document {document_id}")
                return True  # Not an error, just no results
                
        except Exception as e:
            logger.error(f"❌ Error in {analysis_type} specialized analysis for document {document_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _get_cached_visual_analysis(self, document_id: int) -> List[Dict]:
        """Get cached visual analysis results from the backend"""
        try:
            endpoint = f"{self.backend_url}/api/dojo/internal/get-cached-visual-analysis"
            payload = {"document_id": document_id}
            
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("success") and result.get("analysis_results"):
                logger.info(f"📥 Retrieved cached visual analysis for document {document_id}: {len(result['analysis_results'])} pages")
                return result["analysis_results"]
            else:
                logger.warning(f"⚠️ No cached visual analysis found for document {document_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error retrieving cached visual analysis for document {document_id}: {e}")
            return []


    def process_visual_analysis(self, pdf_path: str, document_id: int) -> bool:
        """Process visual analysis for a PDF document (Vision Container task)"""
        try:
            logger.info(f"👁️ Processing visual analysis for document {document_id}: {pdf_path}")
            
            # Run visual analysis using the healthcare template analyzer's method
            full_path = os.path.join(self.mount_path, pdf_path)
            if not os.path.exists(full_path):
                logger.error(f"❌ PDF file not found: {full_path}")
                return False
            
            # Extract company_id from path for directory structure
            path_parts = pdf_path.split('/')
            company_id = path_parts[0] if len(path_parts) > 1 else 'unknown'
            
            # Initialize analyzer and run only visual analysis
            self.analyzer.visual_analysis_results = []
            self.analyzer._analyze_visual_content(full_path, company_id, document_id)
            
            if self.analyzer.visual_analysis_results:
                logger.info(f"✅ Visual analysis completed: {len(self.analyzer.visual_analysis_results)} pages analyzed")
                # Cache the visual analysis results for downstream tasks
                self.analyzer._save_visual_analysis(document_id)
                logger.info(f"💾 Cached visual analysis results for document {document_id}")
                return True
            else:
                logger.error(f"❌ Visual analysis failed - no results generated")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in visual analysis for document {document_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def process_slide_feedback(self, document_id: int) -> bool:
        """Process slide feedback for a document (Vision Container task)"""
        try:
            logger.info(f"💬 Processing slide feedback for document {document_id}")
            
            # For now, slide feedback is generated during visual analysis
            # This task exists for future independent slide feedback generation
            # Currently we just mark it as completed since feedback is already generated
            logger.info(f"ℹ️ Slide feedback is currently generated during visual analysis phase")
            logger.info(f"✅ Slide feedback task completed for document {document_id}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error in slide feedback for document {document_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


def main():
    """Main entry point for GPU processing"""
    if len(sys.argv) != 2:
        print("Usage: python main.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    mount_path = os.environ.get('SHARED_FILESYSTEM_MOUNT_PATH', '/mnt/shared')
    backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
    
    try:
        # Initialize processor with healthcare template support
        processor = PDFProcessor(mount_path, backend_url)
        
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