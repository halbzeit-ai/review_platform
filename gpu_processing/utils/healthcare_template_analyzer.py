"""
Healthcare Template-Based Pitch Deck Analyzer
Replaces hardcoded prompts with configurable healthcare sector templates
"""

import os
import json
import time
import logging
import psycopg2
from typing import Dict, List, Optional, Any
from PIL import Image
from io import BytesIO
import ollama
from pdf2image import convert_from_path
import requests

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

class HealthcareTemplateAnalyzer:
    """Template-based pitch deck analyzer for healthcare startups"""
    
    def __init__(self, backend_base_url: str = "http://localhost:8000"):
        self.backend_base_url = backend_base_url
        # Use PostgreSQL database connection
        # Get database host from environment, fallback to CPU server IP
        db_host = os.getenv('DATABASE_HOST', '65.108.32.168')  # CPU server IP
        self.database_url = f"postgresql://review_user:review_password@{db_host}:5432/review-platform"
        
        # Model configuration
        self.vision_model = self.get_model_by_type("vision") or "gemma3:12b"
        self.text_model = self.get_model_by_type("text") or "gemma3:12b"
        self.scoring_model = self.get_model_by_type("scoring") or "phi4:latest"
        
        # Log model configuration
        logger.info(f"🤖 AI Model Configuration:")
        logger.info(f"   📷 Vision Model (slide analysis): {self.vision_model}")
        logger.info(f"   📝 Text Model (offering extraction, name extraction, classification, chapters, questions, specialized analysis): {self.text_model}")
        logger.info(f"   🎯 Scoring Model (question scoring): {self.scoring_model}")
        
        # Analysis results storage
        self.visual_analysis_results = []
        self.company_offering = ""
        self.startup_name = None
        self.classification_result = None
        self.template_config = None
        self.chapter_results = {}
        self.question_results = {}
        self.specialized_results = {}
        
        # Initialize pipeline prompts
        logger.info("🔧 Initializing pipeline prompts from PostgreSQL...")
        self.image_analysis_prompt = self._get_pipeline_prompt("image_analysis")
        self.offering_extraction_prompt = self._get_pipeline_prompt("offering_extraction")
        self.startup_name_extraction_prompt = self._get_pipeline_prompt("startup_name_extraction")
        logger.info(f"📝 Loaded image_analysis_prompt: {self.image_analysis_prompt[:100]}...")
        logger.info(f"📝 Loaded startup_name_extraction_prompt: {self.startup_name_extraction_prompt[:100]}...")
        
        # Project-based storage - read from environment
        self.project_root = os.path.join(os.getenv('SHARED_FILESYSTEM_MOUNT_PATH', '/mnt/CPU-GPU'), 'projects')
    
    def get_model_by_type(self, model_type: str) -> Optional[str]:
        """Get the active model for a specific type from PostgreSQL database"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT model_name FROM model_configs WHERE model_type = %s AND is_active = true LIMIT 1", 
                (model_type,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                logger.info(f"Using configured {model_type} model: {result[0]}")
                return result[0]
        except Exception as e:
            logger.warning(f"Could not get {model_type} model from PostgreSQL: {e}")
        
        return None
    
    def _get_company_info_from_path(self, pdf_path: str) -> tuple:
        """Extract company_id and deck_name from file path"""
        try:
            # Get the filename without extension
            filename = os.path.basename(pdf_path)
            deck_name = os.path.splitext(filename)[0]
            
            # Try to get company info from PostgreSQL database
            try:
                conn = psycopg2.connect(self.database_url)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pd.id, u.company_name, u.email 
                    FROM pitch_decks pd 
                    JOIN users u ON pd.user_id = u.id 
                    WHERE pd.file_path LIKE %s
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
            except Exception as e:
                logger.warning(f"Could not get company info from PostgreSQL: {e}")
            
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
    
    def _get_pipeline_prompt(self, stage_name: str) -> str:
        """Get pipeline prompt from PostgreSQL database"""
        logger.info(f"🔍 Loading {stage_name} prompt from PostgreSQL database")
        
        try:
            import psycopg2
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = %s AND is_active = true LIMIT 1",
                (stage_name,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                logger.info(f"✅ Using configured {stage_name} prompt from PostgreSQL:")
                logger.info(f"📝 Prompt: {result[0]}")
                return result[0]
            else:
                logger.warning(f"❌ No {stage_name} prompt found in PostgreSQL database")
        except Exception as e:
            logger.warning(f"❌ Could not get {stage_name} prompt from PostgreSQL: {e}")
        
        # Default fallback prompts (only used if database is unavailable)
        default_prompts = {
            "image_analysis": "Describe this image and make sure to include anything notable about it (include text you see in the image):",
            "offering_extraction": "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
        }
        
        default_prompt = default_prompts.get(stage_name, f"No default prompt for {stage_name}")
        logger.info(f"⚠️  Using default fallback {stage_name} prompt:")
        logger.info(f"📝 Default prompt: {default_prompt}")
        return default_prompt
    
    def _classify_startup(self, company_offering: str) -> Dict[str, Any]:
        """Classify startup using direct PostgreSQL access and local AI processing"""
        try:
            # Get healthcare sectors from PostgreSQL database
            healthcare_sectors = self._get_healthcare_sectors()
            
            if not healthcare_sectors:
                logger.warning("No healthcare sectors found in database")
                return self._fallback_classification(company_offering)
            
            # Perform classification using local AI models
            return self._perform_local_classification(company_offering, healthcare_sectors)
                
        except Exception as e:
            logger.error(f"Error in local classification: {e}")
            return self._fallback_classification(company_offering)
    
    def _get_healthcare_sectors(self) -> List[Dict[str, Any]]:
        """Get healthcare sectors from PostgreSQL database"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Get healthcare sectors with their associated data
            cursor.execute("""
                SELECT id, name, display_name, description, keywords, sector_focus
                FROM healthcare_sectors 
                WHERE is_active = true 
                ORDER BY id
            """)
            
            sectors = []
            for row in cursor.fetchall():
                sector_id, name, display_name, description, keywords, sector_focus = row
                
                # Parse keywords if they exist
                keywords_list = []
                if keywords:
                    try:
                        import json
                        keywords_list = json.loads(keywords) if isinstance(keywords, str) else keywords
                    except:
                        keywords_list = [keywords] if isinstance(keywords, str) else []
                
                sectors.append({
                    "id": sector_id,
                    "name": name,
                    "display_name": display_name,
                    "description": description or "",
                    "keywords": keywords_list,
                    "sector_focus": sector_focus or ""
                })
            
            conn.close()
            logger.info(f"Retrieved {len(sectors)} healthcare sectors from database")
            return sectors
            
        except Exception as e:
            logger.error(f"Error fetching healthcare sectors: {e}")
            return []
    
    def _perform_local_classification(self, company_offering: str, healthcare_sectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform classification using local AI models and healthcare sector data"""
        try:
            # Create classification prompt with all available sectors
            sector_descriptions = []
            for sector in healthcare_sectors:
                sector_info = f"- {sector['name']}: {sector['description']}"
                if sector['keywords']:
                    sector_info += f" (Keywords: {', '.join(sector['keywords'])})"
                sector_descriptions.append(sector_info)
            
            classification_prompt = f"""
            You are a healthcare venture capital analyst. Classify the following startup offering into the most appropriate healthcare sector.
            
            Available healthcare sectors:
            {chr(10).join(sector_descriptions)}
            
            Company Offering: {company_offering}
            
            Analyze the offering and determine:
            1. Primary healthcare sector (use the exact sector name from the list above)
            2. Confidence score (0.0 to 1.0)
            3. Brief reasoning for the classification
            4. Any secondary sector if applicable
            5. Keywords that matched from the offering
            
            Respond in JSON format:
            {{
                "primary_sector": "exact_sector_name",
                "confidence_score": 0.0-1.0,
                "reasoning": "explanation",
                "secondary_sector": "sector_name_or_null",
                "keywords_matched": ["keyword1", "keyword2"]
            }}
            """
            
            # Use text model for classification
            response = ollama.generate(
                model=self.text_model,
                prompt=classification_prompt,
                options={'num_ctx': 16384, 'temperature': 0.2}  # Low temperature for consistent classification
            )
            
            # Parse JSON response
            import json
            classification_text = response['response'].strip()
            
            # Extract JSON from response (handle cases where model adds extra text)
            start_idx = classification_text.find('{')
            end_idx = classification_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = classification_text[start_idx:end_idx]
                classification_result = json.loads(json_str)
                
                # Find recommended template for the primary sector
                recommended_template = None
                for sector in healthcare_sectors:
                    if sector['name'] == classification_result.get('primary_sector'):
                        # Try to get template associated with this sector
                        template_id = self._get_template_for_sector(sector['id'])
                        recommended_template = template_id
                        break
                
                # Add recommended template and subcategory
                classification_result['recommended_template'] = recommended_template
                classification_result['subcategory'] = classification_result.get('primary_sector', 'General Healthcare')
                
                logger.info(f"Local classification completed: {classification_result['primary_sector']} "
                           f"(confidence: {classification_result.get('confidence_score', 0):.2f})")
                
                return classification_result
            else:
                logger.error("Could not parse JSON from classification response")
                return self._fallback_classification(company_offering)
                
        except Exception as e:
            logger.error(f"Error in local classification: {e}")
            return self._fallback_classification(company_offering)
    
    def _get_template_for_sector(self, sector_id: int) -> Optional[int]:
        """Get recommended template ID for a healthcare sector"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Get templates associated with this sector
            cursor.execute("""
                SELECT id FROM analysis_templates 
                WHERE healthcare_sector_id = %s AND is_active = true 
                ORDER BY is_default DESC, usage_count DESC 
                LIMIT 1
            """, (sector_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting template for sector {sector_id}: {e}")
            return None
    
    def _fallback_classification(self, company_offering: str) -> Dict[str, Any]:
        """Fallback classification when database access fails"""
        logger.warning("Using fallback classification")
        
        # Ultimate fallback
        return {
            "primary_sector": "consumer_health",
            "subcategory": "Health Optimization Tools",
            "confidence_score": 0.3,
            "reasoning": "Fallback classification - unable to access healthcare sectors from database",
            "secondary_sector": None,
            "keywords_matched": [],
            "recommended_template": None
        }
    
    def _load_template_config(self, template_id: Optional[int] = None) -> Dict[str, Any]:
        """Load template configuration from PostgreSQL database"""
        try:
            if not template_id:
                logger.warning("No template ID provided, using fallback configuration")
                return self._get_fallback_template_config()
            
            # Load template details from PostgreSQL
            return self._load_template_from_database(template_id)
                
        except Exception as e:
            logger.error(f"Error loading template configuration: {e}")
            return self._get_fallback_template_config()
    
    def _load_template_from_database(self, template_id: int) -> Dict[str, Any]:
        """Load template configuration directly from PostgreSQL database"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Load template basic info
            cursor.execute("""
                SELECT t.id, t.name, t.description, t.specialized_analysis, 
                       hs.name as sector_name, hs.display_name as sector_display_name
                FROM analysis_templates t
                LEFT JOIN healthcare_sectors hs ON t.healthcare_sector_id = hs.id
                WHERE t.id = %s AND t.is_active = true
            """, (template_id,))
            
            template_row = cursor.fetchone()
            if not template_row:
                logger.warning(f"Template {template_id} not found in database")
                conn.close()
                return self._get_fallback_template_config()
            
            # Parse template data
            t_id, name, description, specialized_analysis, sector_name, sector_display = template_row
            
            # Parse specialized analysis if it exists
            specialized_list = []
            if specialized_analysis:
                try:
                    import json
                    specialized_list = json.loads(specialized_analysis) if isinstance(specialized_analysis, str) else specialized_analysis
                except:
                    specialized_list = []
            
            # Load template chapters and questions
            cursor.execute("""
                SELECT tc.id, tc.chapter_id, tc.name, tc.description, tc.weight, tc.order_index,
                       tc.is_required, tc.enabled
                FROM template_chapters tc
                WHERE tc.template_id = %s AND tc.enabled = true
                ORDER BY tc.order_index
            """, (template_id,))
            
            chapters = []
            for chapter_row in cursor.fetchall():
                chapter_db_id, chapter_id, chapter_name, chapter_desc, weight, order_idx, is_required, enabled = chapter_row
                
                # Load questions for this chapter
                cursor.execute("""
                    SELECT cq.id, cq.question_id, cq.question_text, cq.weight, cq.order_index,
                           cq.enabled, cq.scoring_criteria, cq.healthcare_focus
                    FROM chapter_questions cq
                    WHERE cq.chapter_id = %s AND cq.enabled = true
                    ORDER BY cq.order_index
                """, (chapter_db_id,))
                
                questions = []
                for question_row in cursor.fetchall():
                    q_id, q_question_id, q_text, q_weight, q_order, q_enabled, q_criteria, q_focus = question_row
                    
                    questions.append({
                        "id": q_id,
                        "question_id": q_question_id,
                        "question_text": q_text,
                        "weight": float(q_weight) if q_weight else 1.0,
                        "order_index": q_order,
                        "enabled": q_enabled,
                        "scoring_criteria": q_criteria or "",
                        "healthcare_focus": q_focus or ""
                    })
                
                chapters.append({
                    "id": chapter_db_id,
                    "chapter_id": chapter_id,
                    "name": chapter_name,
                    "description": chapter_desc or "",
                    "weight": float(weight) if weight else 1.0,
                    "order_index": order_idx,
                    "is_required": is_required,
                    "enabled": enabled,
                    "questions": questions
                })
            
            conn.close()
            
            # Format template config in expected structure
            template_config = {
                "template": {
                    "id": t_id,
                    "name": name,
                    "description": description or "",
                    "specialized_analysis": specialized_list,
                    "healthcare_sector": {
                        "name": sector_name,
                        "display_name": sector_display
                    }
                },
                "chapters": chapters
            }
            
            logger.info(f"Loaded template '{name}' with {len(chapters)} chapters from database")
            return template_config
            
        except Exception as e:
            logger.error(f"Error loading template from database: {e}")
            return self._get_fallback_template_config()
    
    def _get_fallback_template_config(self) -> Dict[str, Any]:
        """Comprehensive fallback template configuration based on standard pitch deck analysis"""
        return {
            "template": {
                "id": 0,
                "name": "Comprehensive Startup Analysis Template",
                "description": "Standard venture capital pitch deck analysis template covering all critical areas",
                "specialized_analysis": ["clinical_validation", "regulatory_pathway", "scientific_hypothesis"]
            },
            "chapters": [
                {
                    "id": 1,
                    "chapter_id": "problem_analysis",
                    "name": "Problem Analysis",
                    "description": "Analysis of the problem being addressed and target market",
                    "weight": 1.8,
                    "order_index": 1,
                    "questions": [
                        {
                            "id": 1,
                            "question_id": "target_problem",
                            "question_text": "Who has the problem?",
                            "weight": 2.0,
                            "scoring_criteria": "Clear identification of target audience with specific demographics and characteristics",
                            "healthcare_focus": "Understanding the patient population and healthcare stakeholders affected"
                        },
                        {
                            "id": 2,
                            "question_id": "problem_nature",
                            "question_text": "What exactly is the nature of the problem?",
                            "weight": 2.2,
                            "scoring_criteria": "Detailed problem description with root cause analysis",
                            "healthcare_focus": "Medical or healthcare-specific problem definition with clinical significance"
                        },
                        {
                            "id": 3,
                            "question_id": "pain_points",
                            "question_text": "What are the pain points?",
                            "weight": 2.0,
                            "scoring_criteria": "Specific pain points with impact assessment",
                            "healthcare_focus": "Clinical pain points affecting patient outcomes or healthcare delivery"
                        },
                        {
                            "id": 4,
                            "question_id": "problem_quantification",
                            "question_text": "Can the problem be quantified?",
                            "weight": 1.8,
                            "scoring_criteria": "Quantitative data supporting problem scope and impact",
                            "healthcare_focus": "Clinical metrics, patient numbers, or healthcare cost implications"
                        }
                    ]
                },
                {
                    "id": 2,
                    "chapter_id": "solution_approach",
                    "name": "Solution Approach",
                    "description": "Analysis of the proposed solution and competitive landscape",
                    "weight": 2.0,
                    "order_index": 2,
                    "questions": [
                        {
                            "id": 5,
                            "question_id": "solution_description",
                            "question_text": "What exactly does your solution look like?",
                            "weight": 2.2,
                            "scoring_criteria": "Clear, detailed solution description with implementation approach",
                            "healthcare_focus": "Clinical mechanism, therapeutic approach, or healthcare delivery method"
                        },
                        {
                            "id": 6,
                            "question_id": "differentiation",
                            "question_text": "What distinguishes it from existing solutions?",
                            "weight": 2.0,
                            "scoring_criteria": "Clear competitive differentiation with unique value proposition",
                            "healthcare_focus": "Clinical advantages, regulatory benefits, or improved patient outcomes"
                        },
                        {
                            "id": 7,
                            "question_id": "current_solutions",
                            "question_text": "How does the customer solve the problem currently?",
                            "weight": 1.8,
                            "scoring_criteria": "Understanding of current alternatives and their limitations",
                            "healthcare_focus": "Current standard of care, existing treatments, or workflow solutions"
                        },
                        {
                            "id": 8,
                            "question_id": "competitive_landscape",
                            "question_text": "Are there competitors and what does their solution & positioning look like?",
                            "weight": 1.9,
                            "scoring_criteria": "Comprehensive competitive analysis with positioning comparison",
                            "healthcare_focus": "Competitive healthcare solutions, regulatory status, and market positioning"
                        },
                        {
                            "id": 9,
                            "question_id": "quantified_advantage",
                            "question_text": "Can you quantify your advantage?",
                            "weight": 1.8,
                            "scoring_criteria": "Quantitative metrics demonstrating competitive advantage",
                            "healthcare_focus": "Clinical efficacy data, cost savings, or improved health outcomes"
                        }
                    ]
                },
                {
                    "id": 3,
                    "chapter_id": "product_market_fit",
                    "name": "Product Market Fit",
                    "description": "Analysis of customer validation and market adoption",
                    "weight": 2.1,
                    "order_index": 3,
                    "questions": [
                        {
                            "id": 10,
                            "question_id": "paying_customers",
                            "question_text": "Do you have paying customers?",
                            "weight": 2.5,
                            "scoring_criteria": "Evidence of paying customers with revenue generation",
                            "healthcare_focus": "Healthcare providers, patients, or payers actually purchasing the solution"
                        },
                        {
                            "id": 11,
                            "question_id": "pilot_customers",
                            "question_text": "Do you have non-paying but convinced pilot customers?",
                            "weight": 2.0,
                            "scoring_criteria": "Pilot customers demonstrating product validation and commitment",
                            "healthcare_focus": "Healthcare institutions, clinicians, or patients engaged in pilots"
                        },
                        {
                            "id": 12,
                            "question_id": "customer_acquisition",
                            "question_text": "How did you find them?",
                            "weight": 1.8,
                            "scoring_criteria": "Clear customer acquisition strategy with repeatable process",
                            "healthcare_focus": "Healthcare-specific acquisition channels and relationship building"
                        },
                        {
                            "id": 13,
                            "question_id": "customer_satisfaction",
                            "question_text": "What do users & payers love about your solution?",
                            "weight": 2.0,
                            "scoring_criteria": "Specific customer feedback highlighting value proposition",
                            "healthcare_focus": "Clinical outcomes, workflow improvements, or patient satisfaction"
                        },
                        {
                            "id": 14,
                            "question_id": "churn_analysis",
                            "question_text": "What is the churn and the reasons for it?",
                            "weight": 1.9,
                            "scoring_criteria": "Churn metrics with root cause analysis and mitigation strategies",
                            "healthcare_focus": "Healthcare-specific retention challenges and solutions"
                        }
                    ]
                },
                {
                    "id": 4,
                    "chapter_id": "monetization",
                    "name": "Monetization",
                    "description": "Analysis of revenue model and pricing strategy",
                    "weight": 1.9,
                    "order_index": 4,
                    "questions": [
                        {
                            "id": 15,
                            "question_id": "payer_identification",
                            "question_text": "Who will pay for it?",
                            "weight": 2.2,
                            "scoring_criteria": "Clear identification of paying customers and decision makers",
                            "healthcare_focus": "Healthcare payers, insurance, providers, or patients as payment sources"
                        },
                        {
                            "id": 16,
                            "question_id": "payer_vs_user",
                            "question_text": "Is it the users or someone else?",
                            "weight": 1.8,
                            "scoring_criteria": "Clear distinction between users and payers with rationale",
                            "healthcare_focus": "Healthcare stakeholder payment dynamics and reimbursement models"
                        },
                        {
                            "id": 17,
                            "question_id": "decision_making",
                            "question_text": "What does the buyer's decision-making structure look like?",
                            "weight": 2.0,
                            "scoring_criteria": "Understanding of decision-making process and key stakeholders",
                            "healthcare_focus": "Healthcare procurement, clinical committees, or administrative approval processes"
                        },
                        {
                            "id": 18,
                            "question_id": "sales_cycle",
                            "question_text": "How much time elapses between initial contact and payment?",
                            "weight": 1.8,
                            "scoring_criteria": "Clear sales cycle timeline with key milestones",
                            "healthcare_focus": "Healthcare-specific sales cycles including regulatory and compliance considerations"
                        },
                        {
                            "id": 19,
                            "question_id": "pricing_strategy",
                            "question_text": "How did you design the pricing and why?",
                            "weight": 2.0,
                            "scoring_criteria": "Pricing strategy with market research and value-based rationale",
                            "healthcare_focus": "Healthcare pricing models, reimbursement alignment, and value-based care"
                        },
                        {
                            "id": 20,
                            "question_id": "unit_economics",
                            "question_text": "What are your margins and unit economics?",
                            "weight": 2.1,
                            "scoring_criteria": "Clear unit economics with margin analysis and scalability",
                            "healthcare_focus": "Healthcare-specific cost structure and regulatory compliance costs"
                        }
                    ]
                },
                {
                    "id": 5,
                    "chapter_id": "financials",
                    "name": "Financials",
                    "description": "Analysis of financial metrics and funding requirements",
                    "weight": 2.0,
                    "order_index": 5,
                    "questions": [
                        {
                            "id": 21,
                            "question_id": "monthly_burn",
                            "question_text": "What is your current monthly burn?",
                            "weight": 2.2,
                            "scoring_criteria": "Current burn rate with detailed breakdown",
                            "healthcare_focus": "Healthcare-specific operational costs and regulatory compliance expenses"
                        },
                        {
                            "id": 22,
                            "question_id": "monthly_sales",
                            "question_text": "What are your monthly sales?",
                            "weight": 2.2,
                            "scoring_criteria": "Monthly revenue with growth trends and predictability",
                            "healthcare_focus": "Healthcare revenue recognition and reimbursement timing"
                        },
                        {
                            "id": 23,
                            "question_id": "financial_fluctuations",
                            "question_text": "Are there major fluctuations and why?",
                            "weight": 1.8,
                            "scoring_criteria": "Understanding of financial volatility with explanations",
                            "healthcare_focus": "Healthcare-specific seasonality, reimbursement cycles, or regulatory impacts"
                        },
                        {
                            "id": 24,
                            "question_id": "annual_burn",
                            "question_text": "How much money did you burn last year?",
                            "weight": 1.9,
                            "scoring_criteria": "Historical burn rate with efficiency analysis",
                            "healthcare_focus": "Healthcare development costs, clinical trials, or regulatory expenses"
                        },
                        {
                            "id": 25,
                            "question_id": "funding_requirements",
                            "question_text": "How much funding are you looking for and why exactly this amount?",
                            "weight": 2.3,
                            "scoring_criteria": "Specific funding amount with detailed justification and milestones",
                            "healthcare_focus": "Healthcare-specific funding needs for clinical trials, regulatory approval, or market access"
                        }
                    ]
                },
                {
                    "id": 6,
                    "chapter_id": "use_of_funds",
                    "name": "Use of Funds",
                    "description": "Analysis of investment strategy and future plans",
                    "weight": 1.8,
                    "order_index": 6,
                    "questions": [
                        {
                            "id": 26,
                            "question_id": "fund_allocation",
                            "question_text": "What will you do with the money?",
                            "weight": 2.2,
                            "scoring_criteria": "Detailed fund allocation with specific use cases and timelines",
                            "healthcare_focus": "Healthcare-specific investments in clinical development, regulatory processes, or market access"
                        },
                        {
                            "id": 27,
                            "question_id": "priority_deficits",
                            "question_text": "Is there a ranked list of deficits to address?",
                            "weight": 2.0,
                            "scoring_criteria": "Prioritized list of organizational gaps with investment rationale",
                            "healthcare_focus": "Healthcare-specific capabilities like clinical expertise, regulatory affairs, or quality systems"
                        },
                        {
                            "id": 28,
                            "question_id": "investment_strategy",
                            "question_text": "Can you tell us about your investment strategy?",
                            "weight": 1.9,
                            "scoring_criteria": "Clear investment strategy with risk management and milestone planning",
                            "healthcare_focus": "Healthcare development strategy including clinical phases and regulatory pathways"
                        },
                        {
                            "id": 29,
                            "question_id": "future_state",
                            "question_text": "What will your company look like at the end of this investment period?",
                            "weight": 2.1,
                            "scoring_criteria": "Clear vision of future state with specific metrics and capabilities",
                            "healthcare_focus": "Healthcare milestones including clinical data, regulatory approvals, or market penetration"
                        }
                    ]
                },
                {
                    "id": 7,
                    "chapter_id": "organization",
                    "name": "Organization",
                    "description": "Analysis of team, experience, and organizational maturity",
                    "weight": 1.7,
                    "order_index": 7,
                    "questions": [
                        {
                            "id": 30,
                            "question_id": "team_experience",
                            "question_text": "Who are you and what experience do you have?",
                            "weight": 2.2,
                            "scoring_criteria": "Team backgrounds with relevant experience and track record",
                            "healthcare_focus": "Healthcare industry experience, clinical expertise, or regulatory knowledge"
                        },
                        {
                            "id": 31,
                            "question_id": "organizational_maturity",
                            "question_text": "How can your organizational maturity be described/quantified?",
                            "weight": 1.8,
                            "scoring_criteria": "Organizational structure, processes, and governance maturity",
                            "healthcare_focus": "Healthcare-specific organizational requirements like quality systems or clinical governance"
                        },
                        {
                            "id": 32,
                            "question_id": "team_composition",
                            "question_text": "How many people are you / pie chart of people per unit?",
                            "weight": 1.7,
                            "scoring_criteria": "Team size and composition with functional distribution",
                            "healthcare_focus": "Healthcare-specific roles including clinical, regulatory, and quality assurance"
                        },
                        {
                            "id": 33,
                            "question_id": "skill_gaps",
                            "question_text": "What skills are missing in the management team?",
                            "weight": 2.0,
                            "scoring_criteria": "Identified skill gaps with plans for addressing them",
                            "healthcare_focus": "Healthcare-specific expertise gaps in clinical development, regulatory affairs, or commercial strategy"
                        },
                        {
                            "id": 34,
                            "question_id": "urgent_hiring",
                            "question_text": "What are the most urgent positions that need to be filled?",
                            "weight": 2.1,
                            "scoring_criteria": "Prioritized hiring needs with impact on business objectives",
                            "healthcare_focus": "Critical healthcare roles for clinical development, regulatory compliance, or market access"
                        }
                    ]
                }
            ]
        }
    
    def analyze_pdf(self, pdf_path: str, company_id: str = None) -> Dict[str, Any]:
        """Main method to analyze a healthcare startup pitch deck"""
        start_time = time.time()
        logger.info(f"Starting healthcare template analysis of PDF: {pdf_path}")
        
        # Log model configuration at start of analysis
        logger.info(f"🤖 AI Model Configuration:")
        logger.info(f"   📷 Vision Model (slide analysis): {self.vision_model}")
        logger.info(f"   📝 Text Model (offering extraction, name extraction, classification, chapters, questions, specialized analysis): {self.text_model}")
        logger.info(f"   🎯 Scoring Model (question scoring): {self.scoring_model}")
        
        # Clear state from previous analysis sessions
        self.visual_analysis_results = []
        self.company_offering = ""
        self.classification_result = None
        self.template_config = None
        self.chapter_results = {}
        self.question_results = {}
        logger.info("Cleared previous analysis state")
        
        try:
            # Step 1: Convert PDF to images and analyze each page
            self._analyze_visual_content(pdf_path, company_id)
            
            # Step 2: Generate company offering summary
            self._generate_company_offering()
            
            # Step 2.5: Extract startup name
            self._extract_startup_name()
            
            # Step 3: Classify startup based on company offering
            self.classification_result = self._classify_startup(self.company_offering)
            logger.info(f"Startup classified as: {self.classification_result.get('primary_sector')} "
                       f"({self.classification_result.get('confidence_score', 0):.2f} confidence)")
            
            # Step 4: Load appropriate template configuration
            self.template_config = self._load_template_config(
                self.classification_result.get("recommended_template")
            )
            
            # Step 5: Execute template-based analysis
            self._execute_template_analysis()
            
            # Step 6: Generate specialized analysis
            self._generate_specialized_analysis()
            
            processing_time = time.time() - start_time
            logger.info(f"Healthcare template analysis completed in {processing_time:.2f} seconds")
            
            return self._format_healthcare_results(processing_time)
            
        except Exception as e:
            logger.error(f"Error in healthcare template analysis: {e}")
            raise
    
    def _analyze_visual_content(self, pdf_path: str, company_id: str = None):
        """Convert PDF to images and analyze each page with project-based storage"""
        logger.info("Converting PDF to images for visual analysis")
        
        try:
            # Get company and deck information
            if company_id:
                # Use provided company_id
                _, deck_name, deck_id = self._get_company_info_from_path(pdf_path)
            else:
                # Fallback to extracting from path
                company_id, deck_name, deck_id = self._get_company_info_from_path(pdf_path)
            
            # Create project directories
            analysis_path = self._create_project_directories(company_id, deck_name)
            
            # Convert PDF to images
            pages_as_images = convert_from_path(pdf_path, fmt="jpeg")
            total_pages = len(pages_as_images)
            logger.info(f"Processing {total_pages} pages for {company_id}/{deck_name}")
            
            for page_number, page_image in enumerate(pages_as_images):
                logger.info(f"Analyzing page {page_number + 1}/{total_pages}")
                
                # Save slide image to project structure
                slide_filename = f"slide_{page_number + 1}.jpg"
                slide_path = os.path.join(analysis_path, slide_filename)
                page_image.save(slide_path, "JPEG")
                
                # Convert image to bytes for AI analysis
                image_bytes = image_to_byte_array(page_image)
                
                # Get AI analysis of the page
                logger.info(f"🔍 Analyzing page {page_number + 1} with prompt: {self.image_analysis_prompt[:100]}...")
                page_analysis = get_information_for_image(
                    image_bytes, 
                    self.image_analysis_prompt, 
                    self.vision_model
                )
                
                # Store analysis with image path reference (structured format)
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
                
        except Exception as e:
            logger.error(f"Error in visual content analysis: {e}")
            raise
    
    def _generate_company_offering(self):
        """Generate company offering summary"""
        logger.info("Generating company offering summary")
        
        # Extract descriptions from the structured data
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
        # Use pipeline prompt for offering extraction
        offering_prompt = f"{self.offering_extraction_prompt}\n\nPitch deck content: {{pitch_deck_content}}"
        
        try:
            response = ollama.generate(
                model=self.text_model,
                prompt=offering_prompt.format(pitch_deck_content=full_pitchdeck_text),
                options={'num_ctx': 32768, 'temperature': 0.3}
            )
            
            self.company_offering = response['response'].strip()
            logger.info(f"Company offering: {self.company_offering}")
            
        except Exception as e:
            logger.error(f"Error generating company offering: {e}")
            self.company_offering = "Healthcare technology startup"
    
    def _extract_startup_name(self):
        """Extract startup name from pitch deck content"""
        logger.info("Extracting startup name from pitch deck content")
        
        # Extract descriptions from the structured data
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
        try:
            # Use the startup name extraction prompt from database
            startup_name_prompt = f"{self.startup_name_extraction_prompt}\n\nPitch deck content: {{pitch_deck_content}}"
            
            response = ollama.generate(
                model=self.text_model,
                prompt=startup_name_prompt.format(pitch_deck_content=full_pitchdeck_text),
                options={'num_ctx': 32768, 'temperature': 0.1}  # Lower temperature for more accurate extraction
            )
            
            # Clean up the response to extract just the name
            self.startup_name = response['response'].strip()
            
            # Remove common conversational phrases that might slip through
            unwanted_phrases = [
                "the startup is called", "the company is", "the name is", 
                "according to", "based on", "the startup", "the company"
            ]
            
            for phrase in unwanted_phrases:
                if phrase in self.startup_name.lower():
                    # Try to extract just the name part
                    parts = self.startup_name.lower().split(phrase)
                    if len(parts) > 1:
                        self.startup_name = parts[1].strip()
                        break
            
            # Clean up any remaining punctuation
            self.startup_name = self.startup_name.strip('.,!?;:"\'')
            
            logger.info(f"Extracted startup name: {self.startup_name}")
            
        except Exception as e:
            logger.error(f"Error extracting startup name: {e}")
            self.startup_name = None
    
    def _execute_template_analysis(self):
        """Execute analysis based on loaded template"""
        logger.info("Executing template-based analysis")
        
        if not self.template_config or not self.template_config.get("chapters"):
            logger.warning("No template configuration available, skipping template analysis")
            return
        
        # Extract descriptions from the structured data
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
        for chapter in self.template_config["chapters"]:
            chapter_id = chapter["chapter_id"]
            chapter_name = chapter["name"]
            
            logger.info(f"📚 Analyzing chapter: {chapter_name}")
            
            # Process each question in the chapter
            chapter_questions = chapter.get("questions", [])
            chapter_responses = []
            chapter_scores = []
            
            for question in chapter_questions:
                question_id = question["question_id"]
                question_text = question["question_text"]
                scoring_criteria = question.get("scoring_criteria", "")
                healthcare_focus = question.get("healthcare_focus", "")
                
                # Generate question-specific analysis
                question_prompt = f"""
                You are a healthcare venture capital analyst reviewing a pitch deck. 
                
                Healthcare Focus: {healthcare_focus}
                
                Question: {question_text}
                
                Scoring Criteria: {scoring_criteria}
                
                Based on the pitch deck content below, provide a detailed analysis answering this question.
                Focus on healthcare-specific considerations and clinical relevance.
                
                Pitch deck content: {full_pitchdeck_text}
                """
                
                try:
                    response = ollama.generate(
                        model=self.text_model,
                        prompt=question_prompt,
                        options={'num_ctx': 32768, 'temperature': 0.7}
                    )
                    
                    question_response = response['response']
                    chapter_responses.append(question_response)
                    
                    # Generate score for this question
                    score = self._score_question(question_text, scoring_criteria, question_response, full_pitchdeck_text)
                    chapter_scores.append(score)
                    
                    # Store question result
                    self.question_results[question_id] = {
                        "question_text": question_text,
                        "response": question_response,
                        "score": score,
                        "weight": question.get("weight", 1.0),
                        "scoring_criteria": scoring_criteria,
                        "healthcare_focus": healthcare_focus
                    }
                    
                except Exception as e:
                    logger.error(f"Error analyzing question {question_id}: {e}")
                    chapter_responses.append(f"Error analyzing question: {str(e)}")
                    chapter_scores.append(0)
            
            # Calculate chapter-level results
            if chapter_scores:
                # Calculate weighted average score
                weights = [q.get("weight", 1.0) for q in chapter_questions]
                weighted_score = sum(s * w for s, w in zip(chapter_scores, weights)) / sum(weights)
                
                # Build detailed question structure for this chapter
                chapter_question_details = []
                for i, question in enumerate(chapter_questions):
                    question_detail = {
                        "id": question.get("id"),
                        "question_id": question["question_id"],
                        "question_text": question["question_text"],
                        "response": chapter_responses[i] if i < len(chapter_responses) else "",
                        "score": chapter_scores[i] if i < len(chapter_scores) else 0,
                        "weight": question.get("weight", 1.0),
                        "scoring_criteria": question.get("scoring_criteria", ""),
                        "healthcare_focus": question.get("healthcare_focus", "")
                    }
                    chapter_question_details.append(question_detail)
                
                self.chapter_results[chapter_id] = {
                    "name": chapter_name,
                    "description": chapter.get("description", ""),
                    "questions": chapter_question_details,  # New structured format
                    "weighted_score": weighted_score,
                    "weight": chapter.get("weight", 1.0),
                    "total_questions": len(chapter_questions),
                    "code_version": "v2.0-with-questions-array"  # Debug marker
                }
    
    def _score_question(self, question_text: str, scoring_criteria: str, response: str, pitch_deck_text: str) -> int:
        """Score a specific question response"""
        scoring_prompt = f"""
        You are a healthcare venture capital analyst scoring a pitch deck analysis.
        
        Question: {question_text}
        
        Scoring Criteria: {scoring_criteria}
        
        Analysis Response: {response}
        
        Based on the original pitch deck content and the analysis response, provide a score from 0-7 where:
        - 0-1: Very poor, missing critical information
        - 2-3: Poor, limited information provided
        - 4-5: Good, adequate information with some gaps
        - 6-7: Excellent, comprehensive and well-supported information
        
        Consider healthcare-specific requirements and clinical validation needs.
        
        Provide only the numeric score (0-7), no additional text.
        
        Original pitch deck content: {pitch_deck_text}
        """
        
        try:
            response = ollama.generate(
                model=self.scoring_model,
                prompt=scoring_prompt,
                options={'num_ctx': 16384, 'temperature': 0.1}
            )
            
            score_text = response['response'].strip()
            try:
                score = int(score_text.split()[0])
                return max(0, min(7, score))
            except (ValueError, IndexError):
                logger.warning(f"Could not parse score: {score_text}")
                return 3  # Default middle score
                
        except Exception as e:
            logger.error(f"Error scoring question: {e}")
            return 0
    
    def _generate_specialized_analysis(self):
        """Generate specialized analysis based on template configuration"""
        if not self.template_config:
            return
        
        specialized_analyses = self.template_config.get("template", {}).get("specialized_analysis", [])
        
        if not specialized_analyses:
            return
        
        logger.info(f"Generating specialized analysis: {', '.join(specialized_analyses)}")
        
        # Extract descriptions from the structured data
        descriptions = []
        for page_data in self.visual_analysis_results:
            if isinstance(page_data, dict):
                descriptions.append(page_data.get("description", ""))
            else:
                descriptions.append(str(page_data))
        
        full_pitchdeck_text = " ".join(descriptions)
        
        for analysis_type in specialized_analyses:
            try:
                if analysis_type == "clinical_validation":
                    self._generate_clinical_validation_analysis(full_pitchdeck_text)
                elif analysis_type == "regulatory_pathway":
                    self._generate_regulatory_pathway_analysis(full_pitchdeck_text)
                elif analysis_type == "scientific_hypothesis":
                    self._generate_scientific_hypothesis_analysis(full_pitchdeck_text)
                else:
                    logger.warning(f"Unknown specialized analysis type: {analysis_type}")
                    
            except Exception as e:
                logger.error(f"Error in specialized analysis {analysis_type}: {e}")
                self.specialized_results[analysis_type] = f"Error: {str(e)}"
    
    def _generate_clinical_validation_analysis(self, pitch_deck_text: str):
        """Generate clinical validation analysis"""
        prompt = """
        You are a healthcare venture capital analyst with clinical expertise.
        
        Analyze the clinical validation approach described in this pitch deck.
        Focus on:
        - Clinical study design and methodology
        - Clinical endpoints and outcome measures
        - Patient population and inclusion criteria
        - Statistical analysis and power calculations
        - Clinical significance vs. statistical significance
        - Regulatory pathway considerations
        
        Provide a structured analysis of the clinical validation strategy.
        
        Pitch deck content: {pitch_deck_content}
        """
        
        try:
            response = ollama.generate(
                model=self.text_model,
                prompt=prompt.format(pitch_deck_content=pitch_deck_text),
                options={'num_ctx': 16384, 'temperature': 0.5}
            )
            
            self.specialized_results["clinical_validation"] = response['response']
            
        except Exception as e:
            logger.error(f"Error in clinical validation analysis: {e}")
            self.specialized_results["clinical_validation"] = f"Error: {str(e)}"
    
    def _generate_regulatory_pathway_analysis(self, pitch_deck_text: str):
        """Generate regulatory pathway analysis"""
        prompt = """
        You are a healthcare regulatory expert analyzing a pitch deck.
        
        Analyze the regulatory pathway and strategy described in this pitch deck.
        Focus on:
        - FDA classification and regulatory pathway
        - Clinical trial requirements and phases
        - Regulatory timeline and milestones
        - Regulatory risks and mitigation strategies
        - International regulatory considerations
        - Compliance and quality systems
        
        Provide a structured analysis of the regulatory strategy.
        
        Pitch deck content: {pitch_deck_content}
        """
        
        try:
            response = ollama.generate(
                model=self.text_model,
                prompt=prompt.format(pitch_deck_content=pitch_deck_text),
                options={'num_ctx': 16384, 'temperature': 0.5}
            )
            
            self.specialized_results["regulatory_pathway"] = response['response']
            
        except Exception as e:
            logger.error(f"Error in regulatory pathway analysis: {e}")
            self.specialized_results["regulatory_pathway"] = f"Error: {str(e)}"
    
    def _generate_scientific_hypothesis_analysis(self, pitch_deck_text: str):
        """Generate scientific hypothesis analysis"""
        prompt = """
        You are a medical doctor and scientist reviewing a healthcare startup pitch deck.
        
        Identify and analyze the core scientific hypotheses underlying this healthcare solution.
        Focus on:
        - Biological or physiological mechanisms
        - Clinical hypotheses and rationale
        - Scientific evidence supporting the hypotheses
        - Potential gaps or limitations in the scientific approach
        - Research methodology and validation
        
        Provide a numbered list of core scientific hypotheses with analysis.
        
        Pitch deck content: {pitch_deck_content}
        """
        
        try:
            response = ollama.generate(
                model=self.text_model,
                prompt=prompt.format(pitch_deck_content=pitch_deck_text),
                options={'num_ctx': 16384, 'temperature': 0.5}
            )
            
            self.specialized_results["scientific_hypothesis"] = response['response']
            
        except Exception as e:
            logger.error(f"Error in scientific hypothesis analysis: {e}")
            self.specialized_results["scientific_hypothesis"] = f"Error: {str(e)}"
    
    def _format_healthcare_results(self, processing_time: float) -> Dict[str, Any]:
        """Format results in healthcare-focused structure"""
        # Calculate overall score
        if self.chapter_results:
            chapter_scores = []
            chapter_weights = []
            
            for chapter_id, chapter_data in self.chapter_results.items():
                chapter_scores.append(chapter_data["weighted_score"])
                chapter_weights.append(chapter_data["weight"])
            
            overall_score = sum(s * w for s, w in zip(chapter_scores, chapter_weights)) / sum(chapter_weights)
        else:
            overall_score = 0.0
        
        # Log template processing results after calculation
        template_name = self.template_config.get("template", {}).get("name", "Fallback Template") if self.template_config else "Fallback Template"
        sector_name = self.classification_result.get("primary_sector", "Unknown") if self.classification_result else "Unknown"
        confidence = self.classification_result.get("confidence_score", 0.0) if self.classification_result else 0.0
        
        logger.info(f"🎉 Analysis Complete - Template Processing Results:")
        logger.info(f"   📊 Total slides analyzed: {len(self.visual_analysis_results)}")
        logger.info(f"   🏥 Healthcare sector classified: {sector_name} (confidence: {confidence:.2f})")
        logger.info(f"   📋 Template used: {template_name}")
        logger.info(f"   📚 Chapters processed: {len(self.chapter_results)}")
        logger.info(f"   ❓ Questions analyzed: {len(self.question_results)}")
        logger.info(f"   🔬 Specialized analyses: {len(self.specialized_results)}")
        logger.info(f"   🎯 Overall score: {overall_score:.1f}/7")
        
        return {
            "company_offering": self.company_offering,
            "startup_name": self.startup_name,
            "classification": self.classification_result,
            "template_used": self.template_config.get("template", {}) if self.template_config else None,
            "overall_score": overall_score,
            "chapter_analysis": self.chapter_results,
            "question_analysis": self.question_results,
            "specialized_analysis": self.specialized_results,
            "visual_analysis_results": self.visual_analysis_results,  # Include slide-by-slide analysis
            "processing_metadata": {
                "processing_time": processing_time,
                "model_versions": {
                    "vision_model": self.vision_model,
                    "text_model": self.text_model,
                    "scoring_model": self.scoring_model
                },
                "total_pages_analyzed": len(self.visual_analysis_results),
                "classification_confidence": self.classification_result.get("confidence_score", 0.0) if self.classification_result else 0.0,
                "template_id": self.template_config.get("template", {}).get("id") if self.template_config else None
            }
        }