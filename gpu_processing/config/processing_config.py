"""
Configuration settings for GPU processing
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load GPU-specific environment variables
load_dotenv(Path(__file__).parent.parent / ".env.gpu")

@dataclass
class ProcessingConfig:
    """Configuration for AI processing parameters"""
    
    # File paths
    mount_path: str = "/mnt/CPU-GPU"
    uploads_dir: str = "uploads"
    results_dir: str = "results"
    temp_dir: str = "temp"
    models_dir: str = "models"
    
    # Processing parameters
    max_processing_time: int = 300  # 5 minutes
    chunk_size: int = 1000  # For text processing
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    
    # AI model settings
    model_name: str = "default"
    device: str = "cuda"  # or "cpu"
    batch_size: int = 16
    max_length: int = 512
    temperature: float = 0.7
    
    # Scoring thresholds
    min_score: float = 0.0
    max_score: float = 10.0
    confidence_threshold: float = 0.5
    
    # Output settings
    include_raw_text: bool = False
    include_debug_info: bool = False
    output_format: str = "json"
    
    @classmethod
    def from_env(cls) -> "ProcessingConfig":
        """Load configuration from environment variables"""
        return cls(
            mount_path=os.getenv("SHARED_FILESYSTEM_MOUNT_PATH", "/mnt/CPU-GPU"),
            max_processing_time=int(os.getenv("MAX_PROCESSING_TIME", "300")),
            device=os.getenv("PROCESSING_DEVICE", "cuda"),
            batch_size=int(os.getenv("BATCH_SIZE", "16")),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            include_debug_info=os.getenv("INCLUDE_DEBUG_INFO", "false").lower() == "true",
        )
    
    @property
    def uploads_path(self) -> Path:
        """Full path to uploads directory"""
        return Path(self.mount_path) / self.uploads_dir
    
    @property
    def results_path(self) -> Path:
        """Full path to results directory"""
        return Path(self.mount_path) / self.results_dir
    
    @property
    def temp_path(self) -> Path:
        """Full path to temp directory"""
        return Path(self.mount_path) / self.temp_dir
    
    @property
    def models_path(self) -> Path:
        """Full path to models directory"""
        return Path(self.mount_path) / self.models_dir


# Default configuration instance
config = ProcessingConfig.from_env()

# AI Processing Templates
PROCESSING_TEMPLATES = {
    "summary": "Provide a concise summary of this pitch deck focusing on the key business opportunity and value proposition.",
    "key_points": "Extract the most important points from this pitch deck, focusing on market opportunity, team, and business model.",
    "recommendations": "Based on the pitch deck content, provide specific recommendations for improving the business proposal.",
    "analysis": "Analyze the following aspects: market size, team strength, business model, traction, and potential risks."
}

# Scoring criteria
SCORING_CRITERIA = {
    "market_opportunity": {
        "weight": 0.25,
        "description": "Size and growth potential of the target market"
    },
    "team_strength": {
        "weight": 0.20,
        "description": "Experience and expertise of the founding team"
    },
    "business_model": {
        "weight": 0.20,
        "description": "Clarity and viability of the revenue model"
    },
    "traction": {
        "weight": 0.15,
        "description": "Evidence of market validation and early success"
    },
    "product_innovation": {
        "weight": 0.10,
        "description": "Uniqueness and innovation of the product/service"
    },
    "financials": {
        "weight": 0.10,
        "description": "Quality and realism of financial projections"
    }
}

# Expected PDF sections
EXPECTED_SECTIONS = [
    "Executive Summary",
    "Problem Statement",
    "Solution Overview", 
    "Market Analysis",
    "Product Description",
    "Business Model",
    "Go-to-Market Strategy",
    "Competitive Analysis",
    "Team Overview",
    "Financial Projections",
    "Funding Requirements",
    "Next Steps"
]