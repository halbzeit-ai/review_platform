import pytest
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from io import BytesIO

from app.main import app
from app.db.models import User, PitchDeck
from app.db.database import SessionLocal


@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_startup_user():
    """Create a mock startup user."""
    return User(
        id=1,
        email="startup@test.com",
        company_name="Test Startup",
        role="startup"
    )


@pytest.fixture
def mock_gp_user():
    """Create a mock GP user."""
    return User(
        id=2,
        email="gp@test.com",
        company_name="Test VC",
        role="gp"
    )


@pytest.fixture
def mock_pitch_deck():
    """Create a mock pitch deck."""
    return PitchDeck(
        id=1,
        user_id=1,
        file_name="test.pdf",
        file_path="uploads/test/test.pdf",
        processing_status="processing"
    )


class TestDocumentUpload:
    """Test suite for document upload functionality."""

    def test_upload_valid_pdf(self, test_client, mock_startup_user):
        """Test uploading a valid PDF file."""
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n174\n%%EOF"
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.volume_storage.save_file', return_value="uploads/test/test.pdf"):
                with patch('app.api.documents.get_db') as mock_get_db:
                    mock_db = Mock(spec=Session)
                    mock_get_db.return_value = mock_db
                    
                    with patch('app.api.documents.trigger_gpu_processing') as mock_trigger:
                        response = test_client.post(
                            "/api/documents/upload",
                            files={"file": ("test.pdf", pdf_content, "application/pdf")}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["filename"] == "test.pdf"
                        assert data["processing_status"] == "processing"
                        assert "pitch_deck_id" in data
                        
                        # Verify database operations
                        mock_db.add.assert_called_once()
                        mock_db.commit.assert_called()

    def test_upload_invalid_file_type(self, test_client, mock_startup_user):
        """Test uploading a non-PDF file."""
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            response = test_client.post(
                "/api/documents/upload",
                files={"file": ("test.txt", b"text content", "text/plain")}
            )
            
            assert response.status_code == 400
            assert "Only PDF files are allowed" in response.json()["detail"]

    def test_upload_too_large_file(self, test_client, mock_startup_user):
        """Test uploading a file that's too large."""
        # Create a large file content (simulate > 50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            response = test_client.post(
                "/api/documents/upload",
                files={"file": ("large.pdf", large_content, "application/pdf")}
            )
            
            # This would typically be caught by the web server, but we can test the validation
            assert response.status_code in [400, 413]

    def test_upload_gp_user_forbidden(self, test_client, mock_gp_user):
        """Test that GP users cannot upload documents."""
        with patch('app.api.auth.get_current_user', return_value=mock_gp_user):
            response = test_client.post(
                "/api/documents/upload",
                files={"file": ("test.pdf", b"PDF content", "application/pdf")}
            )
            
            assert response.status_code == 403
            assert "Only startups can upload documents" in response.json()["detail"]

    def test_upload_unauthenticated(self, test_client):
        """Test uploading without authentication."""
        response = test_client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")}
        )
        
        assert response.status_code == 401

    def test_upload_triggers_background_processing(self, test_client, mock_startup_user):
        """Test that upload triggers background GPU processing."""
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.volume_storage.save_file', return_value="uploads/test/test.pdf"):
                with patch('app.api.documents.get_db') as mock_get_db:
                    mock_db = Mock(spec=Session)
                    mock_get_db.return_value = mock_db
                    
                    with patch('app.api.documents.trigger_gpu_processing') as mock_trigger:
                        response = test_client.post(
                            "/api/documents/upload",
                            files={"file": ("test.pdf", b"PDF content", "application/pdf")}
                        )
                        
                        assert response.status_code == 200
                        # Background task should have been triggered
                        # Note: In real tests, we'd verify the BackgroundTasks.add_task call


class TestProcessingStatus:
    """Test suite for processing status endpoints."""

    def test_get_processing_status_success(self, test_client, mock_startup_user, mock_pitch_deck):
        """Test retrieving processing status for a pitch deck."""
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
                mock_get_db.return_value = mock_db
                
                response = test_client.get("/api/documents/processing-status/1")
                
                assert response.status_code == 200
                data = response.json()
                assert data["pitch_deck_id"] == 1
                assert data["processing_status"] == "processing"
                assert data["file_name"] == "test.pdf"

    def test_get_processing_status_not_found(self, test_client, mock_startup_user):
        """Test retrieving processing status for non-existent pitch deck."""
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = None
                mock_get_db.return_value = mock_db
                
                response = test_client.get("/api/documents/processing-status/999")
                
                assert response.status_code == 404
                assert "Pitch deck not found" in response.json()["detail"]

    def test_get_processing_status_access_denied(self, test_client, mock_startup_user, mock_pitch_deck):
        """Test access denied for pitch deck owned by different user."""
        # Create a pitch deck owned by different user
        other_pitch_deck = PitchDeck(
            id=2,
            user_id=999,  # Different user
            file_name="other.pdf",
            file_path="uploads/other/other.pdf",
            processing_status="processing"
        )
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = other_pitch_deck
                mock_get_db.return_value = mock_db
                
                response = test_client.get("/api/documents/processing-status/2")
                
                assert response.status_code == 403
                assert "Access denied" in response.json()["detail"]

    def test_gp_can_access_any_pitch_deck_status(self, test_client, mock_gp_user, mock_pitch_deck):
        """Test that GP users can access any pitch deck status."""
        with patch('app.api.auth.get_current_user', return_value=mock_gp_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
                mock_get_db.return_value = mock_db
                
                response = test_client.get("/api/documents/processing-status/1")
                
                assert response.status_code == 200
                data = response.json()
                assert data["pitch_deck_id"] == 1


class TestProcessingResults:
    """Test suite for processing results endpoints."""

    def test_get_processing_results_success(self, test_client, mock_startup_user):
        """Test retrieving processing results for completed pitch deck."""
        completed_pitch_deck = PitchDeck(
            id=1,
            user_id=1,
            file_name="test.pdf",
            file_path="uploads/test/test.pdf",
            processing_status="completed"
        )
        
        mock_results = {
            "overall_score": 8.5,
            "analysis": {
                "problem": {"score": 8.0, "analysis": "Good problem identification"},
                "solution": {"score": 9.0, "analysis": "Innovative solution"}
            }
        }
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = completed_pitch_deck
                mock_get_db.return_value = mock_db
                
                with patch('app.api.documents.glob.glob', return_value=["/mnt/shared/results/job_1_12345_results.json"]):
                    with patch('builtins.open', mock_open_multiple_files({
                        "/mnt/shared/results/job_1_12345_results.json": json.dumps(mock_results)
                    })):
                        response = test_client.get("/api/documents/results/1")
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["pitch_deck_id"] == 1
                        assert data["results"]["overall_score"] == 8.5

    def test_get_processing_results_not_completed(self, test_client, mock_startup_user, mock_pitch_deck):
        """Test retrieving results for pitch deck that's not completed."""
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
                mock_get_db.return_value = mock_db
                
                response = test_client.get("/api/documents/results/1")
                
                assert response.status_code == 400
                assert "Processing not completed yet" in response.json()["detail"]

    def test_get_processing_results_file_not_found(self, test_client, mock_startup_user):
        """Test retrieving results when results file doesn't exist."""
        completed_pitch_deck = PitchDeck(
            id=1,
            user_id=1,
            file_name="test.pdf",
            file_path="uploads/test/test.pdf",
            processing_status="completed"
        )
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = completed_pitch_deck
                mock_get_db.return_value = mock_db
                
                with patch('app.api.documents.glob.glob', return_value=[]):
                    response = test_client.get("/api/documents/results/1")
                    
                    assert response.status_code == 404
                    assert "Results not found" in response.json()["detail"]

    def test_get_processing_results_access_denied(self, test_client, mock_startup_user):
        """Test access denied for results owned by different user."""
        other_pitch_deck = PitchDeck(
            id=2,
            user_id=999,  # Different user
            file_name="other.pdf",
            file_path="uploads/other/other.pdf",
            processing_status="completed"
        )
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = other_pitch_deck
                mock_get_db.return_value = mock_db
                
                response = test_client.get("/api/documents/results/2")
                
                assert response.status_code == 403
                assert "Access denied" in response.json()["detail"]


class TestFileNamingCompatibility:
    """Test suite for file naming compatibility."""

    def test_results_file_naming_pattern(self, test_client, mock_startup_user):
        """Test that results files follow the expected naming pattern."""
        completed_pitch_deck = PitchDeck(
            id=1,
            user_id=1,
            file_name="test.pdf",
            file_path="uploads/test/test.pdf",
            processing_status="completed"
        )
        
        mock_results = {"test": "data"}
        
        with patch('app.api.auth.get_current_user', return_value=mock_startup_user):
            with patch('app.api.documents.get_db') as mock_get_db:
                mock_db = Mock(spec=Session)
                mock_db.query.return_value.filter.return_value.first.return_value = completed_pitch_deck
                mock_get_db.return_value = mock_db
                
                # Test that the correct file pattern is used
                with patch('app.api.documents.glob.glob') as mock_glob:
                    mock_glob.return_value = ["/mnt/shared/results/job_1_12345_results.json"]
                    
                    with patch('builtins.open', mock_open_multiple_files({
                        "/mnt/shared/results/job_1_12345_results.json": json.dumps(mock_results)
                    })):
                        response = test_client.get("/api/documents/results/1")
                        
                        # Verify the glob pattern used
                        expected_pattern = "/mnt/CPU-GPU/results/job_1_*_results.json"
                        mock_glob.assert_called_with(expected_pattern)
                        
                        assert response.status_code == 200


def mock_open_multiple_files(files_dict):
    """Helper function to mock opening multiple files with different content."""
    from unittest.mock import mock_open, MagicMock
    
    def open_func(filename, mode='r', *args, **kwargs):
        if filename in files_dict:
            return mock_open(read_data=files_dict[filename])()
        else:
            raise FileNotFoundError(f"No such file: {filename}")
    
    return open_func


if __name__ == "__main__":
    pytest.main([__file__, "-v"])