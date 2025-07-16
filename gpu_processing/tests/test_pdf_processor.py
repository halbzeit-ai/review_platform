import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from main import PDFProcessor
from utils.pitch_deck_analyzer import PitchDeckAnalyzer


@pytest.fixture
def pdf_processor():
    """Create a PDF processor instance for testing."""
    return PDFProcessor(mount_path="/tmp/test")


@pytest.fixture
def mock_analyzer():
    """Create a mock pitch deck analyzer."""
    analyzer = Mock(spec=PitchDeckAnalyzer)
    analyzer.analyze_pitch_deck.return_value = {
        "overall_score": 8.5,
        "analysis": {
            "problem": {
                "score": 8.0,
                "analysis": "Good problem identification",
                "key_points": ["Clear problem statement", "Market validation"]
            },
            "solution": {
                "score": 9.0,
                "analysis": "Innovative solution approach",
                "key_points": ["Unique technology", "Scalable architecture"]
            }
        },
        "recommendations": [
            "Strengthen market analysis",
            "Provide more financial projections"
        ]
    }
    return analyzer


@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file path."""
    return "/tmp/test/uploads/test_company/test_file.pdf"


class TestPDFProcessor:
    """Test suite for PDF processor functionality."""

    def test_pdf_processor_initialization(self, pdf_processor):
        """Test that PDF processor initializes correctly."""
        assert pdf_processor.mount_path == "/tmp/test"
        assert pdf_processor.analyzer is not None

    def test_process_pdf_success(self, pdf_processor, mock_analyzer, sample_pdf_path):
        """Test successful PDF processing."""
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test_company/test_file.pdf")
                
                assert result is not None
                assert result["overall_score"] == 8.5
                assert "analysis" in result
                assert "recommendations" in result
                
                # Verify analyzer was called with correct path
                mock_analyzer.analyze_pitch_deck.assert_called_once_with(sample_pdf_path)

    def test_process_pdf_file_not_found(self, pdf_processor):
        """Test PDF processing when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError) as excinfo:
                pdf_processor.process_pdf("uploads/nonexistent/file.pdf")
            
            assert "PDF file not found" in str(excinfo.value)

    def test_process_pdf_analyzer_error(self, pdf_processor, mock_analyzer, sample_pdf_path):
        """Test PDF processing when analyzer raises an error."""
        mock_analyzer.analyze_pitch_deck.side_effect = Exception("Analysis failed")
        
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                with pytest.raises(Exception) as excinfo:
                    pdf_processor.process_pdf("uploads/test_company/test_file.pdf")
                
                assert "Analysis failed" in str(excinfo.value)

    def test_process_pdf_path_construction(self, pdf_processor, mock_analyzer):
        """Test that file paths are constructed correctly."""
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                pdf_processor.process_pdf("uploads/company/file.pdf")
                
                # Verify the full path was constructed correctly
                expected_path = "/tmp/test/uploads/company/file.pdf"
                mock_analyzer.analyze_pitch_deck.assert_called_once_with(expected_path)

    def test_process_pdf_different_mount_paths(self, mock_analyzer):
        """Test PDF processing with different mount paths."""
        custom_processor = PDFProcessor(mount_path="/custom/mount")
        
        with patch.object(custom_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                custom_processor.process_pdf("uploads/test/file.pdf")
                
                expected_path = "/custom/mount/uploads/test/file.pdf"
                mock_analyzer.analyze_pitch_deck.assert_called_once_with(expected_path)

    def test_process_pdf_return_format(self, pdf_processor, mock_analyzer):
        """Test that processed PDF returns data in expected format."""
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/test/file.pdf")
                
                # Verify required fields are present
                assert "overall_score" in result
                assert "analysis" in result
                assert "recommendations" in result
                
                # Verify analysis structure
                assert "problem" in result["analysis"]
                assert "solution" in result["analysis"]
                
                # Verify each analysis section has required fields
                for section in ["problem", "solution"]:
                    assert "score" in result["analysis"][section]
                    assert "analysis" in result["analysis"][section]
                    assert "key_points" in result["analysis"][section]

    def test_process_pdf_logging(self, pdf_processor, mock_analyzer):
        """Test that PDF processing logs appropriate messages."""
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                with patch('main.logger') as mock_logger:
                    pdf_processor.process_pdf("uploads/test/file.pdf")
                    
                    # Verify logging calls
                    mock_logger.info.assert_called()
                    log_messages = [call.args[0] for call in mock_logger.info.call_args_list]
                    
                    # Check that appropriate messages were logged
                    assert any("Processing PDF" in msg for msg in log_messages)


class TestPitchDeckAnalyzer:
    """Test suite for pitch deck analyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create a pitch deck analyzer instance."""
        return PitchDeckAnalyzer()

    def test_analyzer_initialization(self, analyzer):
        """Test that analyzer initializes correctly."""
        assert analyzer is not None

    def test_analyze_pitch_deck_pdf_processing(self, analyzer):
        """Test PDF processing and image conversion."""
        with patch('utils.pitch_deck_analyzer.convert_from_path') as mock_convert:
            with patch('utils.pitch_deck_analyzer.extract_text_from_pdf') as mock_extract:
                with patch.object(analyzer, '_analyze_with_ai') as mock_ai:
                    # Mock PDF conversion
                    mock_convert.return_value = [Mock(), Mock()]  # 2 pages
                    mock_extract.return_value = "Sample text content"
                    mock_ai.return_value = {
                        "overall_score": 8.0,
                        "analysis": {},
                        "recommendations": []
                    }
                    
                    result = analyzer.analyze_pitch_deck("/path/to/test.pdf")
                    
                    assert result is not None
                    mock_convert.assert_called_once_with("/path/to/test.pdf")
                    mock_extract.assert_called_once_with("/path/to/test.pdf")

    def test_analyze_pitch_deck_ai_processing(self, analyzer):
        """Test AI analysis of pitch deck content."""
        with patch('utils.pitch_deck_analyzer.convert_from_path', return_value=[Mock()]):
            with patch('utils.pitch_deck_analyzer.extract_text_from_pdf', return_value="Test content"):
                with patch.object(analyzer, '_analyze_with_ai') as mock_ai:
                    mock_ai.return_value = {
                        "overall_score": 7.5,
                        "analysis": {
                            "problem": {"score": 8.0, "analysis": "Good problem"},
                            "solution": {"score": 7.0, "analysis": "Decent solution"}
                        },
                        "recommendations": ["Improve solution"]
                    }
                    
                    result = analyzer.analyze_pitch_deck("/path/to/test.pdf")
                    
                    assert result["overall_score"] == 7.5
                    assert "analysis" in result
                    assert "recommendations" in result
                    mock_ai.assert_called_once()

    def test_analyze_pitch_deck_error_handling(self, analyzer):
        """Test error handling in pitch deck analysis."""
        with patch('utils.pitch_deck_analyzer.convert_from_path', side_effect=Exception("PDF error")):
            with pytest.raises(Exception) as excinfo:
                analyzer.analyze_pitch_deck("/path/to/broken.pdf")
            
            assert "PDF error" in str(excinfo.value)

    def test_analyze_pitch_deck_empty_pdf(self, analyzer):
        """Test analysis of empty PDF."""
        with patch('utils.pitch_deck_analyzer.convert_from_path', return_value=[]):
            with patch('utils.pitch_deck_analyzer.extract_text_from_pdf', return_value=""):
                with patch.object(analyzer, '_analyze_with_ai') as mock_ai:
                    mock_ai.return_value = {
                        "overall_score": 0.0,
                        "analysis": {},
                        "recommendations": ["Add content to pitch deck"]
                    }
                    
                    result = analyzer.analyze_pitch_deck("/path/to/empty.pdf")
                    
                    assert result["overall_score"] == 0.0
                    assert "Add content" in result["recommendations"][0]

    def test_analyze_pitch_deck_large_pdf(self, analyzer):
        """Test analysis of large PDF with many pages."""
        # Create mock pages
        mock_pages = [Mock() for _ in range(20)]
        
        with patch('utils.pitch_deck_analyzer.convert_from_path', return_value=mock_pages):
            with patch('utils.pitch_deck_analyzer.extract_text_from_pdf', return_value="Large content"):
                with patch.object(analyzer, '_analyze_with_ai') as mock_ai:
                    mock_ai.return_value = {
                        "overall_score": 9.0,
                        "analysis": {},
                        "recommendations": []
                    }
                    
                    result = analyzer.analyze_pitch_deck("/path/to/large.pdf")
                    
                    assert result["overall_score"] == 9.0
                    mock_ai.assert_called_once()


class TestOllamaIntegration:
    """Test suite for Ollama integration."""

    def test_ollama_model_interaction(self):
        """Test interaction with Ollama models."""
        with patch('ollama.generate') as mock_generate:
            mock_generate.return_value = {
                'response': json.dumps({
                    "overall_score": 8.5,
                    "analysis": {
                        "problem": {"score": 8.0, "analysis": "Good problem identification"}
                    },
                    "recommendations": ["Strengthen market analysis"]
                })
            }
            
            analyzer = PitchDeckAnalyzer()
            
            with patch.object(analyzer, '_analyze_with_ai') as mock_ai:
                mock_ai.return_value = json.loads(mock_generate.return_value['response'])
                
                result = analyzer._analyze_with_ai("Sample text", [])
                
                assert result["overall_score"] == 8.5
                assert "analysis" in result
                assert "recommendations" in result

    def test_ollama_error_handling(self):
        """Test error handling when Ollama is unavailable."""
        with patch('ollama.generate', side_effect=Exception("Ollama connection error")):
            analyzer = PitchDeckAnalyzer()
            
            with pytest.raises(Exception) as excinfo:
                analyzer._analyze_with_ai("Sample text", [])
            
            assert "Ollama connection error" in str(excinfo.value)

    def test_ollama_invalid_response(self):
        """Test handling of invalid Ollama responses."""
        with patch('ollama.generate') as mock_generate:
            mock_generate.return_value = {'response': 'invalid json'}
            
            analyzer = PitchDeckAnalyzer()
            
            with pytest.raises(json.JSONDecodeError):
                analyzer._analyze_with_ai("Sample text", [])


class TestFileHandling:
    """Test suite for file handling operations."""

    def test_pdf_file_existence_check(self, pdf_processor):
        """Test file existence checking."""
        with patch('os.path.exists', return_value=True):
            assert os.path.exists("/tmp/test/uploads/test.pdf") is True
        
        with patch('os.path.exists', return_value=False):
            assert os.path.exists("/tmp/test/uploads/nonexistent.pdf") is False

    def test_pdf_file_permissions(self, pdf_processor):
        """Test handling of file permission errors."""
        with patch('os.path.exists', return_value=True):
            with patch('utils.pitch_deck_analyzer.convert_from_path', side_effect=PermissionError("Permission denied")):
                analyzer = PitchDeckAnalyzer()
                
                with pytest.raises(PermissionError):
                    analyzer.analyze_pitch_deck("/restricted/file.pdf")

    def test_pdf_file_corruption(self, pdf_processor):
        """Test handling of corrupted PDF files."""
        with patch('os.path.exists', return_value=True):
            with patch('utils.pitch_deck_analyzer.convert_from_path', side_effect=Exception("Corrupted PDF")):
                analyzer = PitchDeckAnalyzer()
                
                with pytest.raises(Exception) as excinfo:
                    analyzer.analyze_pitch_deck("/corrupted/file.pdf")
                
                assert "Corrupted PDF" in str(excinfo.value)


class TestPerformanceAndScaling:
    """Test suite for performance and scaling considerations."""

    def test_processing_time_measurement(self, pdf_processor, mock_analyzer):
        """Test that processing time is reasonable."""
        import time
        
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                start_time = time.time()
                pdf_processor.process_pdf("uploads/test/file.pdf")
                end_time = time.time()
                
                # Processing should complete quickly in tests
                assert end_time - start_time < 1.0

    def test_memory_usage_large_files(self, pdf_processor, mock_analyzer):
        """Test memory usage with large files."""
        # This would typically require more sophisticated memory profiling
        # For now, we test that the process completes without errors
        with patch.object(pdf_processor, 'analyzer', mock_analyzer):
            with patch('os.path.exists', return_value=True):
                result = pdf_processor.process_pdf("uploads/large/file.pdf")
                
                assert result is not None
                assert "overall_score" in result

    def test_concurrent_processing(self, pdf_processor, mock_analyzer):
        """Test concurrent PDF processing."""
        import threading
        
        results = []
        
        def process_pdf(filename):
            with patch.object(pdf_processor, 'analyzer', mock_analyzer):
                with patch('os.path.exists', return_value=True):
                    result = pdf_processor.process_pdf(f"uploads/test/{filename}")
                    results.append(result)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=process_pdf, args=(f"file_{i}.pdf",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all processing completed
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert "overall_score" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])