"""
PDF content extraction utilities
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

# PDF processing imports (will be installed on GPU instances)
try:
    import PyPDF2
    import pdfplumber
    import fitz  # PyMuPDF
    PDF_LIBS_AVAILABLE = True
except ImportError:
    PDF_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFExtractor:
    """Extract content from PDF files for AI processing"""
    
    def __init__(self):
        if not PDF_LIBS_AVAILABLE:
            logger.warning("PDF processing libraries not available. Install PyPDF2, pdfplumber, and PyMuPDF.")
    
    def extract_content(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive content from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing extracted content
        """
        if not PDF_LIBS_AVAILABLE:
            return self._placeholder_extraction(pdf_path)
        
        try:
            content = {
                "text": self._extract_text(pdf_path),
                "images": self._extract_images(pdf_path),
                "structure": self._extract_structure(pdf_path),
                "metadata": self._extract_metadata(pdf_path)
            }
            
            logger.info(f"Successfully extracted content from {pdf_path}")
            return content
            
        except Exception as e:
            logger.error(f"Error extracting content from {pdf_path}: {e}")
            return self._placeholder_extraction(pdf_path)
    
    def _extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text content from PDF"""
        text_content = {
            "full_text": "",
            "pages": [],
            "word_count": 0,
            "sections": []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_text = ""
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    text_content["pages"].append({
                        "page_number": page_num + 1,
                        "text": page_text,
                        "char_count": len(page_text)
                    })
                    all_text += page_text + "\n"
                
                text_content["full_text"] = all_text
                text_content["word_count"] = len(all_text.split())
                text_content["sections"] = self._identify_sections(all_text)
                
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            text_content["error"] = str(e)
        
        return text_content
    
    def _extract_images(self, pdf_path: str) -> Dict[str, Any]:
        """Extract images and visual elements from PDF"""
        images_content = {
            "image_count": 0,
            "images": [],
            "charts_detected": False,
            "diagrams_detected": False
        }
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    images_content["images"].append({
                        "page": page_num + 1,
                        "index": img_index,
                        "size": img[2:4],  # width, height
                        "type": "image"
                    })
                
                images_content["image_count"] = len(image_list)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            images_content["error"] = str(e)
        
        return images_content
    
    def _extract_structure(self, pdf_path: str) -> Dict[str, Any]:
        """Extract document structure and layout"""
        structure_content = {
            "page_count": 0,
            "outline": [],
            "headings": [],
            "layout_analysis": {}
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                structure_content["page_count"] = len(pdf.pages)
                
                # Extract outline/bookmarks if available
                if hasattr(pdf, 'outline'):
                    structure_content["outline"] = pdf.outline
                
                # Analyze layout patterns
                for page_num, page in enumerate(pdf.pages):
                    # Extract text with formatting information
                    chars = page.chars
                    if chars:
                        # Identify potential headings by font size
                        font_sizes = [char.get('size', 0) for char in chars]
                        if font_sizes:
                            avg_font_size = sum(font_sizes) / len(font_sizes)
                            large_text = [char for char in chars if char.get('size', 0) > avg_font_size * 1.2]
                            
                            if large_text:
                                structure_content["headings"].append({
                                    "page": page_num + 1,
                                    "potential_headings": len(large_text)
                                })
                
        except Exception as e:
            logger.error(f"Error extracting structure: {e}")
            structure_content["error"] = str(e)
        
        return structure_content
    
    def _extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = {
            "file_size": 0,
            "creation_date": None,
            "modification_date": None,
            "title": None,
            "author": None,
            "subject": None,
            "creator": None,
            "producer": None
        }
        
        try:
            # File size
            metadata["file_size"] = Path(pdf_path).stat().st_size
            
            # PDF metadata
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pdf_metadata = pdf_reader.metadata
                
                if pdf_metadata:
                    metadata.update({
                        "title": pdf_metadata.get('/Title'),
                        "author": pdf_metadata.get('/Author'),
                        "subject": pdf_metadata.get('/Subject'),
                        "creator": pdf_metadata.get('/Creator'),
                        "producer": pdf_metadata.get('/Producer'),
                        "creation_date": str(pdf_metadata.get('/CreationDate')),
                        "modification_date": str(pdf_metadata.get('/ModDate'))
                    })
                
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            metadata["error"] = str(e)
        
        return metadata
    
    def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """Identify potential sections in the text"""
        sections = []
        
        # Common section headers in pitch decks
        section_keywords = [
            "executive summary", "problem", "solution", "market",
            "business model", "competition", "team", "financial",
            "funding", "next steps", "appendix"
        ]
        
        text_lower = text.lower()
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if line contains section keywords
            for keyword in section_keywords:
                if keyword in line_lower and len(line.strip()) < 100:
                    sections.append({
                        "line_number": i + 1,
                        "text": line.strip(),
                        "keyword": keyword,
                        "confidence": 0.8 if line_lower.startswith(keyword) else 0.5
                    })
                    break
        
        return sections
    
    def _placeholder_extraction(self, pdf_path: str) -> Dict[str, Any]:
        """Placeholder extraction when PDF libraries are not available"""
        return {
            "text": {
                "full_text": "PDF extraction not available - libraries not installed",
                "pages": [],
                "word_count": 0,
                "sections": []
            },
            "images": {
                "image_count": 0,
                "images": [],
                "charts_detected": False,
                "diagrams_detected": False
            },
            "structure": {
                "page_count": 0,
                "outline": [],
                "headings": [],
                "layout_analysis": {}
            },
            "metadata": {
                "file_size": Path(pdf_path).stat().st_size if Path(pdf_path).exists() else 0,
                "extraction_method": "placeholder"
            }
        }