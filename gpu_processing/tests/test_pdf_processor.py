import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from main import PDFProcessor
from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer


@pytest.fixture
def pdf_processor():
    """Create a PDF processor instance for testing."""
    return PDFProcessor(mount_path="/tmp/test")


@pytest.fixture
def mock_healthcare_analyzer():
    """Create a mock healthcare template analyzer."""
    analyzer = Mock(spec=HealthcareTemplateAnalyzer)
    analyzer.analyze_pdf.return_value = {
        "company_offering": "AI-powered medical device for surgical assistance",
        "startup_name": "TestMed Inc",
        "funding_amount": "€2M",
        "deck_date": "January 2025",
        "classification": "medtech",
        "chapter_analysis": {
            "Problem Analysis": {
                "score": 6.5,
                "analysis": "Well-defined healthcare problem",
                "questions": [
                    {
                        "question": "Is the problem clearly defined?",
                        "answer": "Yes, the problem is well-articulated",
                        "score": 7.0
                    }
                ]
            },
            "Solution Approach": {
                "score": 7.2,
                "analysis": "Innovative AI-based solution",
                "questions": [
                    {
                        "question": "Is the solution technically feasible?",
                        "answer": "The technology appears sound",
                        "score": 8.0
                    }
                ]
            }
        },
        "specialized_analysis": {
            "clinical_validation": "Phase I trials completed",
            "regulatory_pathway": "CE marking pathway identified", 
            "scientific_hypothesis": "AI can improve surgical precision"
        },
        "visual_analysis_results": [
            {
                "page": 1,
                "description": "Title slide with company logo"
            },
            {
                "page": 2, 
                "description": "Problem statement slide"
            }
        ],
        "processing_metadata": {
            "processing_time": 180.5,
            "total_slides": 12,
            "model_versions": {
                "vision_model": "gemma3:12b",
                "text_model": "gemma3:12b",
                "score_model": "phi4:latest"
            }
        }
    }
    return analyzer


@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file path."""
    return "/tmp/test/uploads/testmed/test_pitch.pdf"


class TestPDFProcessor:
    """Test suite for PDF processor functionality."""

    def test_pdf_processor_initialization(self, pdf_processor):
        """Test that PDF processor initializes correctly."""
        assert pdf_processor.mount_path == "/tmp/test"
        assert pdf_processor.analyzer is not None
        assert isinstance(pdf_processor.analyzer, HealthcareTemplateAnalyzer)

    def test_process_pdf_success(self, pdf_processor, mock_healthcare_analyzer, sample_pdf_path):
        """Test successful PDF processing with healthcare template analyzer."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/testmed/test_pitch.pdf", "testmed")
                
                assert result is not None
                assert "company_offering" in result
                assert "startup_name" in result
                assert "chapter_analysis" in result
                assert "specialized_analysis" in result
                
                # Verify analyzer was called with correct parameters
                mock_healthcare_analyzer.analyze_pdf.assert_called_once_with(sample_pdf_path, "testmed")

    def test_process_pdf_file_not_found(self, pdf_processor):
        """Test PDF processing when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError) as excinfo:
                pdf_processor.process_pdf("uploads/nonexistent/file.pdf")
            
            assert "PDF file not found" in str(excinfo.value)

    def test_process_pdf_analyzer_error(self, pdf_processor, mock_healthcare_analyzer, sample_pdf_path):
        """Test PDF processing when healthcare analyzer raises an error."""
        mock_healthcare_analyzer.analyze_pdf.side_effect = Exception("Healthcare analysis failed")
        
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/testmed/test_pitch.pdf")
                
                # Should return error structure instead of raising
                assert "error" in result
                assert "Healthcare analysis failed" in result["error"]

    def test_process_pdf_path_construction(self, pdf_processor, mock_healthcare_analyzer):
        """Test that file paths are constructed correctly."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                pdf_processor.process_pdf("uploads/company/file.pdf", "company")
                
                # Verify the full path was constructed correctly
                expected_path = "/tmp/test/uploads/company/file.pdf"
                mock_healthcare_analyzer.analyze_pdf.assert_called_once_with(expected_path, "company")

    def test_process_pdf_different_mount_paths(self, mock_healthcare_analyzer):
        """Test PDF processing with different mount paths."""
        custom_processor = PDFProcessor(mount_path="/custom/mount")
        
        with patch.object(custom_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                custom_processor.process_pdf("uploads/test/file.pdf", "test")
                
                expected_path = "/custom/mount/uploads/test/file.pdf"
                mock_healthcare_analyzer.analyze_pdf.assert_called_once_with(expected_path, "test")

    def test_enhance_healthcare_results_format(self, pdf_processor, mock_healthcare_analyzer):
        """Test that healthcare results are properly enhanced for backward compatibility."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                
                # Verify enhanced format includes backward compatibility fields
                assert "summary" in result
                assert "score" in result
                assert "key_points" in result
                assert "recommendations" in result
                assert "analysis" in result

    def test_process_pdf_healthcare_specific_fields(self, pdf_processor, mock_healthcare_analyzer):
        """Test that healthcare-specific fields are preserved."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                
                # Verify healthcare-specific fields are present
                assert "company_offering" in result
                assert "startup_name" in result
                assert "funding_amount" in result
                assert "classification" in result
                assert "specialized_analysis" in result
                assert "clinical_validation" in result["specialized_analysis"]
                assert "regulatory_pathway" in result["specialized_analysis"]

    def test_process_pdf_logging(self, pdf_processor, mock_healthcare_analyzer):
        """Test that PDF processing logs appropriate messages."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                with patch('main.logger') as mock_logger:
                    pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                    
                    # Verify logging calls
                    mock_logger.info.assert_called()
                    log_messages = [call.args[0] for call in mock_logger.info.call_args_list]
                    
                    # Check that appropriate messages were logged
                    assert any("Processing PDF" in msg for msg in log_messages)
                    assert any("Healthcare template analysis completed successfully" in msg for msg in log_messages)


class TestHealthcareTemplateIntegration:
    """Test suite for healthcare template analyzer integration."""

    def test_healthcare_analyzer_initialization(self, pdf_processor):
        """Test that healthcare analyzer is properly initialized."""
        assert isinstance(pdf_processor.analyzer, HealthcareTemplateAnalyzer)
        assert pdf_processor.analyzer.backend_base_url is not None

    def test_healthcare_template_processing(self, pdf_processor, mock_healthcare_analyzer):
        """Test healthcare template-specific processing."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/medtech/device.pdf", "medtech")
                
                # Verify healthcare template structure
                assert result["classification"] == "medtech"
                assert "Problem Analysis" in result["chapter_analysis"]
                assert "Solution Approach" in result["chapter_analysis"]
                
                # Verify specialized analysis
                specialized = result["specialized_analysis"]
                assert "clinical_validation" in specialized
                assert "regulatory_pathway" in specialized
                assert "scientific_hypothesis" in specialized


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_healthcare_analyzer_database_error(self, pdf_processor, mock_healthcare_analyzer):
        """Test handling of database connection errors."""
        mock_healthcare_analyzer.analyze_pdf.side_effect = Exception("Database connection failed")
        
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                
                assert "error" in result
                assert "Database connection failed" in result["error"]

    def test_pdf_processing_timeout(self, pdf_processor, mock_healthcare_analyzer):
        """Test handling of processing timeouts."""
        mock_healthcare_analyzer.analyze_pdf.side_effect = TimeoutError("Processing timeout")
        
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                
                assert "error" in result
                assert "Processing timeout" in result["error"]


class TestBackwardCompatibility:
    """Test suite for backward compatibility with legacy results format."""

    def test_legacy_results_fields_present(self, pdf_processor, mock_healthcare_analyzer):
        """Test that legacy result fields are still present for backward compatibility."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                
                # Legacy fields that should be present
                legacy_fields = ["summary", "score", "key_points", "recommendations", "analysis"]
                for field in legacy_fields:
                    assert field in result, f"Legacy field '{field}' missing from results"

    def test_enhanced_results_structure(self, pdf_processor, mock_healthcare_analyzer):
        """Test that enhanced results maintain proper structure."""
        with patch.object(pdf_processor, 'analyzer', mock_healthcare_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf", "test")
                
                # Verify analysis structure for backward compatibility
                assert isinstance(result["analysis"], dict)
                assert isinstance(result["key_points"], list)
                assert isinstance(result["recommendations"], list)
                assert isinstance(result["score"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])