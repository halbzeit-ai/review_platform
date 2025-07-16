import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add the parent directory to the Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_ollama():
    """Mock Ollama for testing."""
    with patch('ollama.list') as mock_list:
        with patch('ollama.generate') as mock_generate:
            with patch('ollama.pull') as mock_pull:
                with patch('ollama.delete') as mock_delete:
                    # Set up default mock responses
                    mock_list.return_value = [
                        Mock(model='gemma3:12b', size=8149190253, modified_at='2025-01-01T00:00:00Z', digest='abc123'),
                        Mock(model='phi4:latest', size=9053116391, modified_at='2025-01-01T01:00:00Z', digest='def456')
                    ]
                    
                    mock_generate.return_value = {
                        'response': '{"overall_score": 8.5, "analysis": {"problem": {"score": 8.0}}, "recommendations": []}'
                    }
                    
                    mock_pull.return_value = iter([{'status': 'downloading'}, {'status': 'complete'}])
                    mock_delete.return_value = True
                    
                    yield {
                        'list': mock_list,
                        'generate': mock_generate,
                        'pull': mock_pull,
                        'delete': mock_delete
                    }


@pytest.fixture
def mock_pdf_processing():
    """Mock PDF processing libraries."""
    with patch('pdf2image.convert_from_path') as mock_convert:
        with patch('PyPDF2.PdfReader') as mock_reader:
            with patch('pdfplumber.open') as mock_plumber:
                # Mock PDF to image conversion
                mock_convert.return_value = [Mock(), Mock()]  # 2 pages
                
                # Mock PyPDF2 reader
                mock_pdf_reader = Mock()
                mock_pdf_reader.pages = [Mock(), Mock()]
                mock_pdf_reader.pages[0].extract_text.return_value = "Page 1 text"
                mock_pdf_reader.pages[1].extract_text.return_value = "Page 2 text"
                mock_reader.return_value = mock_pdf_reader
                
                # Mock pdfplumber
                mock_plumber_pdf = Mock()
                mock_plumber_pdf.pages = [Mock(), Mock()]
                mock_plumber_pdf.pages[0].extract_text.return_value = "Page 1 text"
                mock_plumber_pdf.pages[1].extract_text.return_value = "Page 2 text"
                mock_plumber.return_value.__enter__.return_value = mock_plumber_pdf
                
                yield {
                    'convert_from_path': mock_convert,
                    'pdf_reader': mock_reader,
                    'plumber': mock_plumber
                }


@pytest.fixture
def sample_pdf_content():
    """Provide sample PDF content for testing."""
    return {
        "text": "This is a sample pitch deck about our revolutionary AI startup. We solve the problem of inefficient data processing.",
        "pages": [
            "Title: Revolutionary AI Startup\nProblem: Inefficient data processing",
            "Solution: Our AI-powered platform\nMarket: $10B market opportunity",
            "Team: Experienced founders\nTraction: 1000+ users",
            "Financials: $1M revenue projected\nFunding: Seeking $5M Series A"
        ]
    }


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock()
    config.mount_path = "/tmp/test"
    config.results_path = "/tmp/test/results"
    config.uploads_path = "/tmp/test/uploads"
    config.max_processing_time = 300
    config.device = "cuda"
    config.model_name = "gemma3:12b"
    return config


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with patch('os.path.exists') as mock_exists:
        with patch('os.makedirs') as mock_makedirs:
            with patch('builtins.open', create=True) as mock_open:
                mock_exists.return_value = True
                mock_makedirs.return_value = None
                
                yield {
                    'exists': mock_exists,
                    'makedirs': mock_makedirs,
                    'open': mock_open
                }


@pytest.fixture
def mock_logging():
    """Mock logging for testing."""
    with patch('logging.getLogger') as mock_logger:
        logger_instance = Mock()
        mock_logger.return_value = logger_instance
        
        yield logger_instance


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        'SHARED_FILESYSTEM_MOUNT_PATH': '/tmp/test',
        'MAX_PROCESSING_TIME': '300',
        'PROCESSING_DEVICE': 'cuda',
        'GPU_HTTP_PORT': '8001',
        'OLLAMA_HOST': '127.0.0.1:11434'
    }
    
    with patch.dict(os.environ, test_env):
        yield


@pytest.fixture
def mock_time():
    """Mock time functions for testing."""
    with patch('time.time') as mock_time:
        mock_time.return_value = 1234567890
        yield mock_time


@pytest.fixture
def sample_analysis_result():
    """Provide sample analysis results for testing."""
    return {
        "overall_score": 8.5,
        "analysis": {
            "problem": {
                "score": 8.0,
                "analysis": "Clear problem identification with market validation",
                "key_points": [
                    "Well-defined problem statement",
                    "Evidence of market need",
                    "Quantified problem impact"
                ]
            },
            "solution": {
                "score": 9.0,
                "analysis": "Innovative solution with clear differentiation",
                "key_points": [
                    "Unique technology approach",
                    "Scalable architecture",
                    "Clear value proposition"
                ]
            },
            "product_market_fit": {
                "score": 7.5,
                "analysis": "Good market fit with room for improvement",
                "key_points": [
                    "Target market identified",
                    "Customer segments defined",
                    "Needs market validation"
                ]
            },
            "monetisation": {
                "score": 8.0,
                "analysis": "Clear revenue model with multiple streams",
                "key_points": [
                    "Subscription model",
                    "Freemium strategy",
                    "Enterprise pricing"
                ]
            },
            "organisation": {
                "score": 7.0,
                "analysis": "Strong founding team with relevant experience",
                "key_points": [
                    "Technical expertise",
                    "Industry experience",
                    "Needs business development"
                ]
            },
            "competition": {
                "score": 8.5,
                "analysis": "Comprehensive competitive analysis",
                "key_points": [
                    "Identified key competitors",
                    "Clear differentiation",
                    "Competitive advantages"
                ]
            },
            "execution": {
                "score": 7.5,
                "analysis": "Solid execution plan with realistic milestones",
                "key_points": [
                    "Clear roadmap",
                    "Realistic timelines",
                    "Resource allocation"
                ]
            }
        },
        "recommendations": [
            "Strengthen market validation with more customer interviews",
            "Provide more detailed financial projections",
            "Expand team with business development expertise",
            "Add more specific competitive analysis",
            "Include risk assessment and mitigation strategies"
        ],
        "confidence": 0.85,
        "processed_by": "gemma3:12b",
        "processing_time": 45.2
    }


# Configure pytest to show more verbose output
def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line(
        "markers", 
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", 
        "unit: marks tests as unit tests"
    )


# Add custom test markers
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add unit test marker by default
        if not any(marker.name in ['integration', 'slow'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Helper functions for tests
def create_mock_response(status_code=200, json_data=None, text=""):
    """Create a mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    mock_response.text = text
    return mock_response


def create_mock_file_content(content):
    """Create mock file content for testing."""
    mock_file = Mock()
    mock_file.read.return_value = content
    mock_file.__enter__.return_value = mock_file
    mock_file.__exit__.return_value = None
    return mock_file