"""
Simplified Pitch Deck Analyzer for Review Platform
Adapted from radlchecker.py for single-file processing without cloud dependencies
"""

import os
import json
import time
import logging
from PIL import Image
from io import BytesIO
import ollama
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

def image_to_byte_array(image: Image) -> bytes:
    """Convert PIL Image to byte array"""
    imgByteArr = BytesIO()
    image.save(imgByteArr, format=image.format)
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr

def get_information_for_image(image_bytes, prompt, model):
    """Generate description for a single image using Ollama"""
    full_response = ''
    try:
        for response in ollama.generate(model=model, 
                                    prompt=prompt,
                                    images=[image_bytes], 
                                    stream=True):
            full_response += response['response']
    except Exception as e:
        logger.error(f"Error processing image with Ollama: {e}")
        raise
    
    return full_response

class PitchDeckAnalyzer:
    """Simplified pitch deck analyzer for single-file processing"""
    
    def __init__(self):
        # Model configuration - get active model from backend configuration
        active_model = self.get_active_model()
        self.llm_model = active_model  # Vision model for image analysis
        self.report_model = active_model  # Text generation model
        self.score_model = active_model  # Scoring model
        self.science_model = active_model  # Scientific hypothesis model
        
        # Analysis results storage
        self.visual_analysis_results = []
        self.report_chapters = {}
        self.report_scores = {}
        self.scientific_hypotheses = ""
        self.company_offering = ""
        
        # Initialize prompts
        self._setup_prompts()
    
    def get_active_model(self) -> str:
        """Get the active model from backend configuration or use default"""
        try:
            import sqlite3
            
            # Try to get active model from backend database
            db_path = "/opt/review-platform/backend/sql_app.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT model_name FROM model_configs WHERE is_active = 1 LIMIT 1")
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    logger.info(f"Using configured active model: {result[0]}")
                    return result[0]
            
        except Exception as e:
            logger.warning(f"Could not get active model from configuration: {e}")
        
        # Fallback to default model
        default_model = "gemma3:12b"
        logger.info(f"Using default model: {default_model}")
        return default_model
    
    def _setup_prompts(self):
        """Initialize all analysis prompts"""
        self.prompts = {
            # Image analysis
            "describe_image": "Describe this image and make sure to include anything notable about it (include text you see in the image):",
            
            # Role and task definitions
            "role": "You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck.",
            "offering": "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.",
            "answers": "Your task is to find answers to the following questions: ",
            "scores": "Your task is to give a score between 0 and 7 based on how much information is provided for the following questions. Just give a number, no explanations.",
            "science": "You are a medical doctor reviewing a pitchdeck of a health startup. Provide a numbered list of core scientific, health related or medical hypothesis that are addressed by the startup. Do not report market size or any other economic hypotheses. Do not mention the name of the product or the company.",
            
            # The 7 core analysis areas
            "problem": "Who has the problem? What exactly is the nature of the problem? What are the pain points? Can the problem be quantified?",
            "solution": "What exactly does your solution look like, what distinguishes it from existing solutions / how does the customer solve the problem so far? Are there competitors and what does their solution & positioning look like? Can you quantify your advantage?",
            "product market fit": "Do you have paying customers, do you have non-paying but convinced pilot customers? How did you find them? What do users & payers love about your solution? What is the churn and the reasons for it?",
            "monetisation": "Who will pay for it? Is it the users of the solution themselves or someone else? What does the buyer's decision-making structure look like, how much time elapses between initial contact and payment? How did you design the pricing and why exactly like this? What are your margins, what are the unit economics?",
            "financials": "What is your current monthly burn? What are your monthly sales? Are there any major fluctuations in these two points? If so, why? How much money did you burn last year? How much funding are you looking for, why exactly this amount?",
            "use of funds": "What will you do with the money? Is there a ranked list of deficits (not only in the product, but maybe also in the organization or marketing / sales process) that you want to address? Can you tell us about your investment strategy? What will your company look like at the end of this investment period?",
            "organisation": "Who are you, what experience do you have, can it be quantified? How can your organizational maturity be described / quantified? How many people are you / pie chart of people per unit? What skills are missing in the management team? What are the most urgent positions that need to be filled?"
        }
        
        # Define which areas to analyze
        self.analysis_areas = [
            "problem", "solution", "product market fit", "monetisation", 
            "financials", "use of funds", "organisation"
        ]
    
    def analyze_pdf(self, pdf_path: str) -> dict:
        """
        Main method to analyze a pitch deck PDF
        
        Args:
            pdf_path: Full path to the PDF file
            
        Returns:
            Dictionary containing complete analysis results
        """
        start_time = time.time()
        logger.info(f"Starting analysis of PDF: {pdf_path}")
        
        try:
            # Step 1: Convert PDF to images and analyze each page
            self._analyze_visual_content(pdf_path)
            
            # Step 2: Generate company offering summary
            self._generate_company_offering()
            
            # Step 3: Generate detailed analysis for each area
            self._generate_detailed_analysis()
            
            # Step 4: Generate scores for each area
            self._generate_scores()
            
            # Step 5: Extract scientific hypotheses
            self._extract_scientific_hypotheses()
            
            processing_time = time.time() - start_time
            logger.info(f"Analysis completed in {processing_time:.2f} seconds")
            
            return self._format_results(processing_time)
            
        except Exception as e:
            logger.error(f"Error analyzing PDF {pdf_path}: {e}")
            raise
    
    def _analyze_visual_content(self, pdf_path: str):
        """Convert PDF to images and analyze each page"""
        logger.info("Converting PDF to images for visual analysis")
        
        try:
            # Convert PDF to images
            pages_as_images = convert_from_path(pdf_path, fmt="jpeg")
            total_pages = len(pages_as_images)
            logger.info(f"Processing {total_pages} pages")
            
            # Analyze each page
            for page_number, page_image in enumerate(pages_as_images):
                logger.info(f"Analyzing page {page_number + 1}/{total_pages}")
                
                # Convert image to bytes
                image_bytes = image_to_byte_array(page_image)
                
                # Get AI analysis of the page
                page_analysis = get_information_for_image(
                    image_bytes, 
                    self.prompts["describe_image"], 
                    self.llm_model
                )
                
                self.visual_analysis_results.append(page_analysis)
                
        except Exception as e:
            logger.error(f"Error in visual content analysis: {e}")
            raise
    
    def _generate_company_offering(self):
        """Generate single sentence company offering description"""
        logger.info("Generating company offering summary")
        
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        
        try:
            self.company_offering = ""
            for response in ollama.generate(
                model=self.report_model,
                prompt=f"{self.prompts['role']} {self.prompts['offering']} Here is the startup's pitchdeck: {full_pitchdeck_text}",
                stream=True,
                options={'num_ctx': 32768}
            ):
                self.company_offering += response['response']
                
        except Exception as e:
            logger.error(f"Error generating company offering: {e}")
            raise
    
    def _generate_detailed_analysis(self):
        """Generate detailed analysis for each of the 7 areas"""
        logger.info("Generating detailed analysis for each area")
        
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        
        for area in self.analysis_areas:
            logger.info(f"Analyzing area: {area}")
            
            try:
                prompt = (f"{self.prompts['role']} {self.prompts['answers']} "
                         f"questions: {self.prompts[area]} "
                         f"Here is the startup's pitchdeck: {full_pitchdeck_text}")
                
                response = ollama.generate(
                    model=self.report_model,
                    prompt=prompt,
                    options={'num_ctx': 32768}
                )
                
                self.report_chapters[area] = response['response']
                
            except Exception as e:
                logger.error(f"Error analyzing area {area}: {e}")
                # Continue with other areas even if one fails
                self.report_chapters[area] = f"Error analyzing {area}: {str(e)}"
    
    def _generate_scores(self):
        """Generate 0-7 scores for each area"""
        logger.info("Generating scores for each area")
        
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        
        for area in self.analysis_areas:
            logger.info(f"Scoring area: {area}")
            
            try:
                prompt = (f"{self.prompts['role']} {self.prompts['scores']} "
                         f"questions: {self.prompts[area]} "
                         f"Here is the startup's pitchdeck: {full_pitchdeck_text}")
                
                response = ollama.generate(
                    model=self.score_model,
                    prompt=prompt,
                    options={'num_ctx': 32768}
                )
                
                # Extract numeric score from response
                score_text = response['response'].strip()
                try:
                    score = int(score_text.split()[0])  # Get first number
                    score = max(0, min(7, score))  # Clamp to 0-7 range
                except (ValueError, IndexError):
                    score = 0  # Default to 0 if parsing fails
                    logger.warning(f"Could not parse score for {area}, defaulting to 0")
                
                self.report_scores[area] = score
                
            except Exception as e:
                logger.error(f"Error scoring area {area}: {e}")
                self.report_scores[area] = 0
    
    def _extract_scientific_hypotheses(self):
        """Extract scientific hypotheses for health/biotech startups"""
        logger.info("Extracting scientific hypotheses")
        
        full_pitchdeck_text = " ".join(self.visual_analysis_results)
        
        try:
            self.scientific_hypotheses = ""
            for response in ollama.generate(
                model=self.science_model,
                prompt=f"{self.prompts['science']} Here's the startup's pitchdeck: {full_pitchdeck_text}",
                stream=True,
                options={'num_ctx': 16384}
            ):
                self.scientific_hypotheses += response['response']
                
        except Exception as e:
            logger.error(f"Error extracting scientific hypotheses: {e}")
            self.scientific_hypotheses = f"Error extracting hypotheses: {str(e)}"
    
    def _format_results(self, processing_time: float) -> dict:
        """Format final results in expected structure"""
        return {
            "company_offering": self.company_offering.strip(),
            "report_chapters": self.report_chapters,
            "report_scores": self.report_scores,
            "scientific_hypotheses": self.scientific_hypotheses.strip(),
            "processing_metadata": {
                "processing_time": processing_time,
                "model_versions": {
                    "vision_model": self.llm_model,
                    "report_model": self.report_model,
                    "score_model": self.score_model,
                    "science_model": self.science_model
                },
                "total_pages_analyzed": len(self.visual_analysis_results),
                "analysis_areas": self.analysis_areas
            }
        }