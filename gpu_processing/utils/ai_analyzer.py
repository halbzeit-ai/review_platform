"""
AI analysis utilities for pitch deck content
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import re
import os

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Structure for AI analysis results"""
    summary: str
    key_points: List[str]
    score: float
    recommendations: List[str]
    analysis: Dict[str, str]
    confidence: float
    sections_analyzed: List[str]

class AIAnalyzer:
    """AI-powered analysis of pitch deck content"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.model_loaded = False
        
        # Get active model from configuration or use defaults
        self.active_model = self.get_active_model()
        logger.info(f"AI Analyzer initialized with model: {self.active_model}")
    
    def get_active_model(self) -> str:
        """Get the active model from backend configuration or use default"""
        try:
            import requests
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
                    return result[0]
            
        except Exception as e:
            logger.warning(f"Could not get active model from configuration: {e}")
        
        # Fallback to default model
        return "gemma3:12b"
    
    def analyze_content(self, content: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze extracted PDF content using AI models
        
        Args:
            content: Dictionary containing extracted PDF content
            
        Returns:
            AnalysisResult with comprehensive analysis
        """
        try:
            # TODO: Replace with actual AI model inference
            return self._placeholder_analysis(content)
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._fallback_analysis(content)
    
    def _placeholder_analysis(self, content: Dict[str, Any]) -> AnalysisResult:
        """
        Placeholder analysis logic - replace with actual AI implementation
        
        This should be replaced with:
        1. Load pre-trained models for business analysis
        2. Process extracted text through NLP pipelines
        3. Analyze business metrics and viability
        4. Generate structured recommendations
        """
        logger.info("Running placeholder AI analysis...")
        
        text_content = content.get("text", {})
        full_text = text_content.get("full_text", "")
        word_count = text_content.get("word_count", 0)
        
        # Simple text-based analysis
        analysis_metrics = self._analyze_text_metrics(full_text)
        
        return AnalysisResult(
            summary=self._generate_summary(full_text, analysis_metrics),
            key_points=self._extract_key_points(full_text, analysis_metrics),
            score=self._calculate_score(analysis_metrics),
            recommendations=self._generate_recommendations(analysis_metrics),
            analysis=self._detailed_analysis(analysis_metrics),
            confidence=0.75,  # Placeholder confidence
            sections_analyzed=self._get_sections_analyzed(text_content)
        )
    
    def _analyze_text_metrics(self, text: str) -> Dict[str, Any]:
        """Analyze text content for business-relevant metrics"""
        text_lower = text.lower()
        
        # Business keyword analysis
        business_keywords = {
            "market": ["market", "customer", "target", "segment", "demand"],
            "product": ["product", "service", "solution", "innovation", "technology"],
            "competition": ["competitor", "competitive", "advantage", "differentiation"],
            "team": ["team", "founder", "experience", "expertise", "background"],
            "financial": ["revenue", "profit", "funding", "investment", "growth"],
            "traction": ["traction", "customer", "validation", "pilot", "partnership"]
        }
        
        keyword_scores = {}
        for category, keywords in business_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            keyword_scores[category] = min(score / 5, 1.0)  # Normalize to 0-1
        
        # Structure analysis
        structure_score = self._analyze_structure(text)
        
        # Content quality indicators
        quality_metrics = {
            "word_count": len(text.split()),
            "readability": self._calculate_readability(text),
            "structure_score": structure_score,
            "keyword_coverage": keyword_scores,
            "has_numbers": bool(re.search(r'\d+', text)),
            "has_financial_data": bool(re.search(r'[$€£¥]\d+|revenue|profit|funding', text_lower))
        }
        
        return quality_metrics
    
    def _analyze_structure(self, text: str) -> float:
        """Analyze document structure quality"""
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if not non_empty_lines:
            return 0.0
        
        # Check for section headers
        potential_headers = 0
        for line in non_empty_lines:
            line_clean = line.strip()
            if (len(line_clean) < 100 and 
                (line_clean.isupper() or 
                 any(keyword in line_clean.lower() for keyword in 
                     ['executive', 'market', 'business', 'team', 'financial', 'problem', 'solution']))):
                potential_headers += 1
        
        # Structure score based on content organization
        header_ratio = potential_headers / len(non_empty_lines)
        return min(header_ratio * 10, 1.0)  # Normalize to 0-1
    
    def _calculate_readability(self, text: str) -> float:
        """Simple readability score"""
        if not text:
            return 0.0
        
        words = text.split()
        sentences = text.split('.')
        
        if len(sentences) == 0:
            return 0.0
        
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Simple readability (lower is better, normalize to 0-1)
        readability = max(0, 1 - (avg_words_per_sentence - 15) / 20)
        return min(readability, 1.0)
    
    def _generate_summary(self, text: str, metrics: Dict[str, Any]) -> str:
        """Generate summary based on content analysis"""
        word_count = metrics.get("word_count", 0)
        keyword_coverage = metrics.get("keyword_coverage", {})
        
        # Determine focus areas based on keyword analysis
        top_categories = sorted(keyword_coverage.items(), key=lambda x: x[1], reverse=True)[:3]
        focus_areas = [cat for cat, score in top_categories if score > 0.3]
        
        if not focus_areas:
            return "This pitch deck presents a business opportunity with limited detailed analysis available."
        
        summary_parts = ["This pitch deck presents a business opportunity with strong focus on"]
        
        if "market" in focus_areas:
            summary_parts.append("market analysis and customer targeting,")
        if "product" in focus_areas:
            summary_parts.append("product innovation and technology solutions,")
        if "team" in focus_areas:
            summary_parts.append("team expertise and experience,")
        if "financial" in focus_areas:
            summary_parts.append("financial projections and growth potential,")
        
        summary = " ".join(summary_parts).rstrip(",") + "."
        
        # Add document quality assessment
        if word_count > 500:
            summary += " The document provides comprehensive coverage of key business areas."
        else:
            summary += " The document provides a concise overview of the business opportunity."
        
        return summary
    
    def _extract_key_points(self, text: str, metrics: Dict[str, Any]) -> List[str]:
        """Extract key points from content"""
        key_points = []
        keyword_coverage = metrics.get("keyword_coverage", {})
        
        # Generate key points based on content analysis
        if keyword_coverage.get("market", 0) > 0.3:
            key_points.append("Strong market opportunity and customer focus")
        
        if keyword_coverage.get("product", 0) > 0.3:
            key_points.append("Innovative product or service offering")
        
        if keyword_coverage.get("team", 0) > 0.3:
            key_points.append("Experienced team with relevant expertise")
        
        if keyword_coverage.get("financial", 0) > 0.3:
            key_points.append("Clear financial projections and growth model")
        
        if keyword_coverage.get("traction", 0) > 0.3:
            key_points.append("Evidence of market validation and traction")
        
        if keyword_coverage.get("competition", 0) > 0.3:
            key_points.append("Competitive analysis and differentiation strategy")
        
        # Default key points if none identified
        if not key_points:
            key_points = [
                "Business opportunity presented",
                "Market potential identified",
                "Solution approach outlined"
            ]
        
        return key_points[:5]  # Limit to 5 key points
    
    def _calculate_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall score based on analysis"""
        keyword_coverage = metrics.get("keyword_coverage", {})
        structure_score = metrics.get("structure_score", 0)
        word_count = metrics.get("word_count", 0)
        
        # Score components
        content_score = sum(keyword_coverage.values()) / len(keyword_coverage)
        structure_bonus = structure_score * 0.5
        length_bonus = min(word_count / 1000, 1.0) * 0.3
        
        # Calculate final score (0-10 scale)
        raw_score = (content_score + structure_bonus + length_bonus) * 10
        return min(max(raw_score, 3.0), 9.5)  # Clamp between 3.0 and 9.5
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        keyword_coverage = metrics.get("keyword_coverage", {})
        
        # Recommendations based on missing or weak areas
        if keyword_coverage.get("market", 0) < 0.3:
            recommendations.append("Strengthen market analysis and customer segmentation")
        
        if keyword_coverage.get("competition", 0) < 0.3:
            recommendations.append("Develop comprehensive competitive analysis")
        
        if keyword_coverage.get("financial", 0) < 0.3:
            recommendations.append("Include detailed financial projections and unit economics")
        
        if keyword_coverage.get("traction", 0) < 0.3:
            recommendations.append("Provide more evidence of market validation and early traction")
        
        if metrics.get("structure_score", 0) < 0.5:
            recommendations.append("Improve document structure and organization")
        
        # Default recommendations
        if not recommendations:
            recommendations = [
                "Focus on customer acquisition strategy",
                "Strengthen competitive positioning",
                "Develop strategic partnerships",
                "Enhance market penetration approach"
            ]
        
        return recommendations[:4]  # Limit to 4 recommendations
    
    def _detailed_analysis(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate detailed analysis of key areas"""
        keyword_coverage = metrics.get("keyword_coverage", {})
        
        analysis = {}
        
        # Market analysis
        market_strength = keyword_coverage.get("market", 0)
        if market_strength > 0.5:
            analysis["market_size"] = "Strong market analysis with clear customer targeting"
        elif market_strength > 0.3:
            analysis["market_size"] = "Moderate market analysis with room for deeper insights"
        else:
            analysis["market_size"] = "Limited market analysis - requires more detailed research"
        
        # Team analysis
        team_strength = keyword_coverage.get("team", 0)
        if team_strength > 0.5:
            analysis["team_strength"] = "Strong team presentation with relevant experience"
        elif team_strength > 0.3:
            analysis["team_strength"] = "Team credentials presented with some detail"
        else:
            analysis["team_strength"] = "Team information limited - expand on expertise and experience"
        
        # Business model analysis
        financial_strength = keyword_coverage.get("financial", 0)
        if financial_strength > 0.5:
            analysis["business_model"] = "Clear revenue model with financial projections"
        elif financial_strength > 0.3:
            analysis["business_model"] = "Basic business model outlined"
        else:
            analysis["business_model"] = "Business model requires more detailed explanation"
        
        # Traction analysis
        traction_strength = keyword_coverage.get("traction", 0)
        if traction_strength > 0.5:
            analysis["traction"] = "Strong evidence of market validation and customer traction"
        elif traction_strength > 0.3:
            analysis["traction"] = "Some traction indicators present"
        else:
            analysis["traction"] = "Limited traction evidence - focus on validation metrics"
        
        # Risk analysis
        analysis["risks"] = "Standard startup risks including market adoption and competitive pressures"
        
        return analysis
    
    def _get_sections_analyzed(self, text_content: Dict[str, Any]) -> List[str]:
        """Get list of sections that were analyzed"""
        sections = text_content.get("sections", [])
        
        if sections:
            return [section.get("text", "Unknown") for section in sections[:6]]
        
        # Default sections
        return [
            "Executive Summary",
            "Market Analysis",
            "Business Model",
            "Team Overview",
            "Financial Projections",
            "Growth Strategy"
        ]
    
    def _fallback_analysis(self, content: Dict[str, Any]) -> AnalysisResult:
        """Fallback analysis when AI processing fails"""
        return AnalysisResult(
            summary="Analysis completed with limited AI processing capabilities",
            key_points=["Content processed", "Basic analysis performed"],
            score=5.0,
            recommendations=["Review content manually", "Apply detailed analysis"],
            analysis={
                "market_size": "Unable to analyze with current capabilities",
                "team_strength": "Unable to analyze with current capabilities",
                "business_model": "Unable to analyze with current capabilities",
                "traction": "Unable to analyze with current capabilities",
                "risks": "Standard startup risks apply"
            },
            confidence=0.3,
            sections_analyzed=["Content analyzed with basic processing"]
        )