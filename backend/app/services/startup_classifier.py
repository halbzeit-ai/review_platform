"""
Startup Classification Service
Classifies startups based on company offering using healthcare sector definitions
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class StartupClassifier:
    """Service for classifying startups into healthcare sectors"""
    
    def __init__(self, db: Session):
        self.db = db
        self.sectors = self._load_healthcare_sectors()
        self.classification_model = self._get_classification_model()
    
    def _load_healthcare_sectors(self) -> List[Dict[str, Any]]:
        """Load healthcare sectors from database"""
        try:
            query = text("""
            SELECT id, name, display_name, description, keywords, subcategories, 
                   confidence_threshold, regulatory_requirements
            FROM healthcare_sectors
            WHERE is_active = TRUE
            ORDER BY display_name
            """)
            
            result = self.db.execute(query).fetchall()
            
            sectors = []
            for row in result:
                sectors.append({
                    "id": row[0],
                    "name": row[1],
                    "display_name": row[2],
                    "description": row[3],
                    "keywords": json.loads(row[4]),
                    "subcategories": json.loads(row[5]),
                    "confidence_threshold": row[6],
                    "regulatory_requirements": json.loads(row[7])
                })
            
            return sectors
            
        except Exception as e:
            logger.error(f"Error loading healthcare sectors: {e}")
            # Rollback any failed transaction
            try:
                self.db.rollback()
            except:
                pass
                
            # Return some basic fallback sectors if database doesn't exist
            return [
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
    
    def _get_classification_model(self) -> str:
        """Get the active classification model from configuration"""
        try:
            # Try to get from model configuration
            query = text("""
            SELECT model_name FROM model_configs 
            WHERE model_type = 'text' AND is_active = TRUE 
            LIMIT 1
            """)
            
            result = self.db.execute(query).fetchone()
            
            if result:
                return result[0]
            else:
                # Default fallback
                return "gemma3:12b"
                
        except Exception as e:
            logger.warning(f"Could not get classification model: {e}")
            # Rollback any failed transaction
            try:
                self.db.rollback()
            except:
                pass
            return "gemma3:12b"
    
    def _keyword_based_classification(self, company_offering: str) -> List[Dict[str, Any]]:
        """Perform keyword-based classification scoring"""
        offering_lower = company_offering.lower()
        sector_scores = []
        
        for sector in self.sectors:
            matched_keywords = []
            keyword_score = 0
            
            for keyword in sector["keywords"]:
                if keyword.lower() in offering_lower:
                    matched_keywords.append(keyword)
                    # Give higher weight to longer, more specific keywords
                    keyword_score += len(keyword.split())
            
            if matched_keywords:
                # Normalize score by number of keywords in sector
                normalized_score = keyword_score / len(sector["keywords"])
                
                sector_scores.append({
                    "sector": sector,
                    "score": normalized_score,
                    "matched_keywords": matched_keywords
                })
        
        # Sort by score descending
        sector_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return sector_scores[:3]  # Return top 3 candidates
    
    def _create_classification_prompt(self, company_offering: str, top_candidates: List[Dict[str, Any]]) -> str:
        """Create classification prompt for AI model"""
        
        # Add all sectors for completeness (primary classification basis)
        all_sectors = []
        for sector in self.sectors:
            all_sectors.append(f"""- {sector['display_name']}: {sector['description']}
  Subcategories: {", ".join(sector['subcategories'])}""")
        
        # Build keyword context if available (supportive information)
        keyword_context = ""
        if top_candidates:
            sector_descriptions = []
            for candidate in top_candidates:
                sector = candidate["sector"]
                sector_descriptions.append(f"""
{sector["display_name"]}:
- Matched keywords: {", ".join(candidate["matched_keywords"])}
- Keyword relevance score: {candidate["score"]:.2f}""")
            keyword_context = f"""

Keyword Analysis Results (supportive context):
{chr(10).join(sector_descriptions)}

Note: These keyword matches are provided as additional context. Base your classification primarily on the company offering description and sector definitions above."""
        
        prompt = f"""
You are a healthcare venture capital analyst. Your task is to classify a startup based on their company offering into one of the healthcare sectors below.

Company Offering: "{company_offering}"

Healthcare Sectors:
{chr(10).join(all_sectors)}{keyword_context}

Analyze the company offering and classify it into the most appropriate healthcare sector. Consider:
1. The primary business focus and target market
2. The type of solution or intervention provided
3. The regulatory requirements and compliance needs
4. The intended users and healthcare setting

Respond in JSON format with the following structure:
{{
  "primary_sector": "sector_name",
  "subcategory": "specific_subcategory",
  "confidence": 0.85,
  "reasoning": "Detailed explanation of why this classification is appropriate, referencing specific aspects of the company offering",
  "secondary_sector": "alternative_sector_name_if_applicable",
  "keywords_matched": ["keyword1", "keyword2", "keyword3"],
  "regulatory_considerations": ["consideration1", "consideration2"],
  "market_focus": "primary_market_description"
}}

Ensure the confidence score reflects how certain you are about the classification (0.0 to 1.0).
"""
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response and extract classification data"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                logger.info(f"Successfully parsed AI JSON: {list(parsed.keys())}")
                return parsed
            else:
                logger.warning(f"No JSON found in AI response: {response[:100]}...")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing AI response JSON: {e}")
            logger.error(f"Response was: {response[:200]}...")
            return {}
    
    def _find_sector_by_name(self, sector_name: str) -> Optional[Dict[str, Any]]:
        """Find sector by name or display_name"""
        for sector in self.sectors:
            if (sector["name"].lower() == sector_name.lower() or 
                sector["display_name"].lower() == sector_name.lower()):
                return sector
        return None
    
    def _get_default_template_id(self, sector_id: int) -> Optional[int]:
        """Get default template ID for a sector, with fallback to regular templates"""
        try:
            # First, try to find a default template
            query = text("""
            SELECT id FROM analysis_templates 
            WHERE healthcare_sector_id = :sector_id AND is_default = TRUE AND is_active = TRUE
            LIMIT 1
            """)
            
            result = self.db.execute(query, {"sector_id": sector_id}).fetchone()
            if result:
                return result[0]
            
            # If no default template found, fall back to first available regular template for the sector
            logger.info(f"No default template found for sector {sector_id}, using fallback")
            fallback_query = text("""
            SELECT id FROM analysis_templates 
            WHERE healthcare_sector_id = :sector_id AND is_active = TRUE
            ORDER BY id ASC
            LIMIT 1
            """)
            
            fallback_result = self.db.execute(fallback_query, {"sector_id": sector_id}).fetchone()
            if fallback_result:
                logger.info(f"Using fallback template {fallback_result[0]} for sector {sector_id}")
                return fallback_result[0]
            
            logger.warning(f"No templates found for sector {sector_id}")
            return None
            
        except Exception as e:
            logger.warning(f"Could not get template for sector {sector_id}: {e}")
            # Rollback any failed transaction
            try:
                self.db.rollback()
            except:
                pass
            return None
    
    async def classify(self, company_offering: str, manual_classification: Optional[str] = None) -> Dict[str, Any]:
        """Main classification method"""
        try:
            # If manual classification provided, use it
            if manual_classification:
                manual_sector = self._find_sector_by_name(manual_classification)
                if manual_sector:
                    template_id = self._get_default_template_id(manual_sector["id"])
                    return {
                        "primary_sector": manual_sector["name"],
                        "subcategory": manual_sector["subcategories"][0] if manual_sector["subcategories"] else "",
                        "confidence_score": 1.0,
                        "reasoning": f"Manual classification to {manual_sector['display_name']}",
                        "secondary_sector": None,
                        "keywords_matched": [],
                        "recommended_template": template_id
                    }
            
            # Step 1: Keyword-based pre-filtering (optional enhancement)
            top_candidates = self._keyword_based_classification(company_offering)
            
            # Step 2: AI-based classification (primary method)
            # Always run AI classification with all sectors, keywords are just supportive
            prompt = self._create_classification_prompt(company_offering, top_candidates)
            
            # Call AI model via GPU HTTP client
            from ..services.gpu_http_client import gpu_http_client
            response = await gpu_http_client.run_classification(
                model_name=self.classification_model,
                prompt=prompt
            )
            
            if not response.get("success"):
                logger.error(f"GPU classification failed: {response.get('error')}")
                # Fallback to keyword-based classification if available
                if top_candidates:
                    best_candidate = top_candidates[0]
                    sector = best_candidate["sector"]
                    template_id = self._get_default_template_id(sector["id"])
                    
                    return {
                        "primary_sector": sector["name"],
                        "subcategory": sector["subcategories"][0] if sector["subcategories"] else "",
                        "confidence_score": min(best_candidate["score"], 0.5),
                        "reasoning": f"GPU classification failed, using keyword match. Error: {response.get('error')}. Matched keywords: {', '.join(best_candidate['matched_keywords'])}",
                        "secondary_sector": None,
                        "keywords_matched": best_candidate["matched_keywords"],
                        "recommended_template": template_id
                    }
                else:
                    # No keywords and GPU failed - return unknown
                    return {
                        "primary_sector": "unknown",
                        "subcategory": "",
                        "confidence_score": 0.0,
                        "reasoning": f"GPU classification failed and no keyword matches found. Error: {response.get('error')}",
                        "secondary_sector": None,
                        "keywords_matched": [],
                        "recommended_template": None
                    }
            
            # Parse AI response
            ai_response_text = response.get('response', '')
            logger.info(f"GPU classification response: {ai_response_text[:200]}...")
            ai_result = self._parse_ai_response(ai_response_text)
            
            if not ai_result:
                # Fallback to keyword-based classification if available
                if top_candidates:
                    best_candidate = top_candidates[0]
                    sector = best_candidate["sector"]
                    template_id = self._get_default_template_id(sector["id"])
                    
                    return {
                        "primary_sector": sector["name"],
                        "subcategory": sector["subcategories"][0] if sector["subcategories"] else "",
                        "confidence_score": min(best_candidate["score"], 0.7),
                        "reasoning": f"Keyword-based classification (AI parsing failed). Matched keywords: {', '.join(best_candidate['matched_keywords'])}",
                        "secondary_sector": None,
                        "keywords_matched": best_candidate["matched_keywords"],
                        "recommended_template": template_id
                    }
                else:
                    # No keywords and AI parsing failed - return unknown
                    return {
                        "primary_sector": "unknown",
                        "subcategory": "",
                        "confidence_score": 0.0,
                        "reasoning": "AI classification response could not be parsed and no keyword matches found",
                        "secondary_sector": None,
                        "keywords_matched": [],
                        "recommended_template": None
                    }
            
            # Step 3: Validate and enhance AI result
            primary_sector = self._find_sector_by_name(ai_result.get("primary_sector", ""))
            
            if not primary_sector:
                # Fallback to best keyword match if available
                if top_candidates:
                    best_candidate = top_candidates[0]
                    sector = best_candidate["sector"]
                    template_id = self._get_default_template_id(sector["id"])
                    
                    return {
                        "primary_sector": sector["name"],
                        "subcategory": sector["subcategories"][0] if sector["subcategories"] else "",
                        "confidence_score": min(best_candidate["score"], 0.6),
                        "reasoning": f"AI classification failed validation, using keyword match. Matched keywords: {', '.join(best_candidate['matched_keywords'])}",
                        "secondary_sector": None,
                        "keywords_matched": best_candidate["matched_keywords"],
                        "recommended_template": template_id
                    }
                else:
                    # No keywords and AI validation failed - return unknown
                    return {
                        "primary_sector": "unknown",
                        "subcategory": "",
                        "confidence_score": 0.0,
                        "reasoning": f"AI classified as '{ai_result.get('primary_sector', '')}' but this sector was not found in database, and no keyword matches available",
                        "secondary_sector": None,
                        "keywords_matched": [],
                        "recommended_template": None
                    }
            
            # Get template for primary sector
            template_id = self._get_default_template_id(primary_sector["id"])
            
            # Validate subcategory
            subcategory = ai_result.get("subcategory", "")
            if subcategory not in primary_sector["subcategories"]:
                subcategory = primary_sector["subcategories"][0] if primary_sector["subcategories"] else ""
            
            # Apply confidence threshold
            confidence = min(ai_result.get("confidence", 0.5), 1.0)
            if confidence < primary_sector["confidence_threshold"]:
                confidence = primary_sector["confidence_threshold"]
            
            final_result = {
                "primary_sector": primary_sector["name"],
                "subcategory": subcategory,
                "confidence_score": confidence,
                "reasoning": ai_result.get("reasoning", "AI-based classification"),
                "secondary_sector": ai_result.get("secondary_sector"),
                "keywords_matched": ai_result.get("keywords_matched", []),
                "recommended_template": template_id
            }
            
            logger.info(f"Final classification result: sector={final_result['primary_sector']}, confidence={final_result['confidence_score']}")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in startup classification: {e}")
            # Return error classification
            return {
                "primary_sector": "unknown",
                "subcategory": "",
                "confidence_score": 0.0,
                "reasoning": f"Classification failed due to error: {str(e)}",
                "secondary_sector": None,
                "keywords_matched": [],
                "recommended_template": None
            }

# Main API function
async def classify_startup_offering(
    company_offering: str,
    db: Session,
    manual_classification: Optional[str] = None
) -> Dict[str, Any]:
    """Classify startup offering into healthcare sector"""
    
    classifier = StartupClassifier(db)
    result = await classifier.classify(company_offering, manual_classification)
    
    return result