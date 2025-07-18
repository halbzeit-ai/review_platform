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
from dotenv import load_dotenv

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
        # Load environment variables from .env.gpu
        load_dotenv('/opt/gpu_processing/.env.gpu')
        
        # Model configuration - get each model type separately
        self.llm_model = self.get_model_by_type("vision") or "gemma3:12b"  # Vision model for image analysis
        self.report_model = self.get_model_by_type("text") or "gemma3:12b"  # Text generation model
        self.score_model = self.get_model_by_type("scoring") or "phi4:latest"  # Scoring model
        self.science_model = self.get_model_by_type("science") or "phi4:latest"  # Scientific hypothesis model
        
        # Analysis results storage
        self.visual_analysis_results = []
        self.report_chapters = {}
        self.report_scores = {}
        self.scientific_hypotheses = ""
        self.company_offering = ""
        
        # Project-based storage - read from environment
        self.project_root = os.path.join(os.getenv('SHARED_FILESYSTEM_MOUNT_PATH', '/mnt/CPU-GPU'), 'projects')
        
        # Initialize prompts
        self._setup_prompts()
    
    def get_model_by_type(self, model_type: str) -> str:
        """Get the active model for a specific type from backend configuration"""
        try:
            import sqlite3
            
            # Try to get active model from backend database
            db_path = "/opt/review-platform/backend/sql_app.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT model_name FROM model_configs WHERE model_type = ? AND is_active = 1 LIMIT 1", (model_type,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    logger.info(f"Using configured {model_type} model: {result[0]}")
                    return result[0]
            
        except Exception as e:
            logger.warning(f"Could not get {model_type} model from configuration: {e}")
        
        # Return None to use fallback in __init__
        return None
    
    def get_pipeline_prompt(self, stage_name: str) -> str:
        """Get configurable prompt for a specific pipeline stage"""
        try:
            import sqlite3
            
            # Try to get prompt from backend database
            db_path = "/opt/review-platform/backend/sql_app.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT prompt_text FROM pipeline_prompts WHERE stage_name = ? AND is_active = 1 LIMIT 1", (stage_name,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    logger.info(f"Using configured prompt for {stage_name}: {result[0][:50]}...")
                    return result[0]
            
        except Exception as e:
            logger.warning(f"Could not get {stage_name} prompt from configuration: {e}")
        
        # Return None to use fallback in _setup_prompts
        return None
    
    def _get_company_info_from_path(self, pdf_path: str) -> tuple:
        """Extract company_id and deck_name from file path"""
        try:
            # Expected path format: /mnt/shared/uploads/company_name/deck_name.pdf
            import sqlite3
            
            # Get the filename without extension
            filename = os.path.basename(pdf_path)
            deck_name = os.path.splitext(filename)[0]
            
            # Try to get company info from database based on the deck
            db_path = "/opt/review-platform/backend/sql_app.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pd.id, u.company_name, u.email 
                    FROM pitch_decks pd 
                    JOIN users u ON pd.user_id = u.id 
                    WHERE pd.file_path LIKE ?
                """, (f"%{filename}%",))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    deck_id, company_name, user_email = result
                    # Use company name as company_id (convert to URL-safe slug)
                    if company_name:
                        import re
                        company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
                    else:
                        # Fallback to email prefix if company name is not available
                        company_id = user_email.split('@')[0]
                    return company_id, deck_name, deck_id
            
            # Fallback: use path-based extraction
            path_parts = pdf_path.split('/')
            if len(path_parts) >= 2:
                company_id = path_parts[-2] if path_parts[-2] != 'uploads' else 'unknown'
                return company_id, deck_name, None
            
            return 'unknown', deck_name, None
            
        except Exception as e:
            logger.warning(f"Could not extract company info from path {pdf_path}: {e}")
            return 'unknown', os.path.splitext(os.path.basename(pdf_path))[0], None
    
    def _create_project_directories(self, company_id: str, deck_name: str) -> str:
        """Create project directory structure and return analysis path"""
        try:
            # Create project structure
            project_path = os.path.join(self.project_root, company_id)
            analysis_path = os.path.join(project_path, "analysis", deck_name)
            uploads_path = os.path.join(project_path, "uploads")
            exports_path = os.path.join(project_path, "exports")
            
            # Create directories
            os.makedirs(analysis_path, exist_ok=True)
            os.makedirs(uploads_path, exist_ok=True)
            os.makedirs(exports_path, exist_ok=True)
            
            logger.info(f"Created project directories for {company_id}/{deck_name} at {analysis_path}")
            return analysis_path
            
        except Exception as e:
            logger.error(f"Error creating project directories: {e}")
            # Fallback to old structure
            return os.path.join("/mnt/shared/temp", "analysis")
    
    def _setup_prompts(self):
        """Initialize all analysis prompts"""
        # Get configurable prompts from database
        image_prompt = self.get_pipeline_prompt("image_analysis") or "Describe this image and make sure to include anything notable about it (include text you see in the image):"
        offering_prompt = self.get_pipeline_prompt("offering_extraction") or "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
        
        self.prompts = {
            # Image analysis (configurable)
            "describe_image": image_prompt,
            
            # Role and task definitions
            "role": "You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck.",
            "offering": offering_prompt,
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
        """Convert PDF to images and analyze each page with project-based storage"""
        logger.info("Converting PDF to images for visual analysis")
        
        try:
            # Get company and deck information
            company_id, deck_name, deck_id = self._get_company_info_from_path(pdf_path)
            
            # Create project directories
            analysis_path = self._create_project_directories(company_id, deck_name)
            
            # Convert PDF to images (pdf2image default resolution)
            pages_as_images = convert_from_path(pdf_path, fmt="jpeg")
            total_pages = len(pages_as_images)
            logger.info(f"Processing {total_pages} pages for {company_id}/{deck_name}")
            
            # Analyze each page
            for page_number, page_image in enumerate(pages_as_images):
                logger.info(f"Analyzing page {page_number + 1}/{total_pages}")
                
                # Save slide image to project structure
                slide_filename = f"slide_{page_number + 1}.jpg"
                slide_path = os.path.join(analysis_path, slide_filename)
                page_image.save(slide_path, "JPEG")
                
                # Convert image to bytes for AI analysis
                image_bytes = image_to_byte_array(page_image)
                
                # Get AI analysis of the page
                page_analysis = get_information_for_image(
                    image_bytes, 
                    self.prompts["describe_image"], 
                    self.llm_model
                )
                
                # Store analysis with image path reference
                page_analysis_data = {
                    "page_number": page_number + 1,
                    "slide_image_path": os.path.join("analysis", deck_name, slide_filename),  # Relative path
                    "description": page_analysis,
                    "company_id": company_id,
                    "deck_name": deck_name,
                    "deck_id": deck_id
                }
                
                self.visual_analysis_results.append(page_analysis_data)
            
            logger.info(f"Saved {total_pages} slide images to {analysis_path}")
            logger.info(f"Using project root: {self.project_root}")
                
        except Exception as e:
            logger.error(f"Error in visual content analysis: {e}")
            raise
    
    def _generate_company_offering(self):
        """Generate single sentence company offering description"""
        logger.info("Generating company offering summary")
        
        # Extract descriptions from the new data structure
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
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
        
        # Extract descriptions from the new data structure
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
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
        
        # Extract descriptions from the new data structure
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
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
        
        # Extract descriptions from the new data structure
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
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
            "visual_analysis_results": self.visual_analysis_results,  # Include slide-by-slide analysis
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