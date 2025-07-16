import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Test configuration
TEST_MOUNT_PATH = "/tmp/test_shared"
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Set up test environment variables."""
    env_vars = {
        'SHARED_FILESYSTEM_MOUNT_PATH': TEST_MOUNT_PATH,
        'DATABASE_URL': TEST_DATABASE_URL,
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, env_vars):
        # Create test directories
        test_paths = [
            Path(TEST_MOUNT_PATH),
            Path(TEST_MOUNT_PATH) / "uploads",
            Path(TEST_MOUNT_PATH) / "results",
            Path(TEST_MOUNT_PATH) / "temp"
        ]
        
        for path in test_paths:
            path.mkdir(parents=True, exist_ok=True)
        
        yield
        
        # Cleanup
        import shutil
        if Path(TEST_MOUNT_PATH).exists():
            shutil.rmtree(TEST_MOUNT_PATH)


@pytest.fixture
def mock_volume_storage():
    """Mock volume storage for testing."""
    with patch('app.core.volume_storage.VolumeStorageService') as mock_storage:
        mock_instance = MagicMock()
        mock_instance.uploads_path = Path(TEST_MOUNT_PATH) / "uploads"
        mock_instance.results_path = Path(TEST_MOUNT_PATH) / "results"
        mock_instance.temp_path = Path(TEST_MOUNT_PATH) / "temp"
        mock_storage.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = '{"success": true}'
        
        mock_client.return_value.post.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    with patch('app.db.database.get_db') as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        yield mock_session


@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_file.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def sample_pitch_deck():
    """Provide sample pitch deck data."""
    return {
        "id": 1,
        "filename": "test_deck.pdf",
        "file_path": "uploads/test_company/test_deck.pdf",
        "status": "uploaded",
        "company_id": 1,
        "created_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_results():
    """Provide sample processing results."""
    return {
        "overall_score": 8.5,
        "analysis": {
            "problem": {
                "score": 8.0,
                "analysis": "Good problem identification",
                "key_points": ["Clear problem statement", "Market validation"]
            },
            "solution": {
                "score": 9.0,
                "analysis": "Innovative solution",
                "key_points": ["Unique approach", "Technical feasibility"]
            }
        },
        "recommendations": [
            "Strengthen market analysis",
            "Provide more financial projections"
        ],
        "confidence": 0.85,
        "processed_by": "gemma3:12b",
        "processing_time": 45.2
    }


# Configure pytest to ignore warnings
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
    
    # Ignore warnings for cleaner output
    config.addinivalue_line(
        "filterwarnings", 
        "ignore::DeprecationWarning"
    )
    config.addinivalue_line(
        "filterwarnings", 
        "ignore::PendingDeprecationWarning"
    )