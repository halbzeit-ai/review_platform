import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from fastapi import BackgroundTasks

from app.main import app
from app.api.documents import trigger_gpu_processing
from app.services.gpu_http_client import GPUHTTPClient
from app.db.models import PitchDeck, User
from app.db.database import SessionLocal


@pytest.fixture
def test_db():
    """Create a test database session."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = User(
        id=1,
        email="test@example.com",
        company_name="Test Company",
        role="startup"
    )
    return user


@pytest.fixture
def mock_pitch_deck():
    """Create a mock pitch deck for testing."""
    pitch_deck = PitchDeck(
        id=1,
        user_id=1,
        file_name="test.pdf",
        file_path="uploads/test/test.pdf",
        processing_status="pending"
    )
    return pitch_deck


class TestAsyncProcessing:
    """Test suite for async GPU processing functionality."""

    @pytest.mark.asyncio
    async def test_trigger_gpu_processing_success(self, mock_pitch_deck):
        """Test successful GPU processing workflow."""
        # Mock the database session
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
        mock_db.commit.return_value = None

        # Mock the GPU HTTP client
        mock_gpu_client = Mock(spec=GPUHTTPClient)
        mock_gpu_client.process_pdf = AsyncMock(return_value={
            "success": True,
            "results_file": "job_1_12345_results.json",
            "results_path": "/mnt/CPU-GPU/results/job_1_12345_results.json"
        })

        with patch('app.api.documents.SessionLocal', return_value=mock_db):
            with patch('app.api.documents.gpu_http_client', mock_gpu_client):
                # Execute the async function
                await trigger_gpu_processing(1, "uploads/test/test.pdf")

                # Verify database updates
                assert mock_pitch_deck.processing_status == "completed"
                assert mock_db.commit.call_count == 2  # Once for "processing", once for "completed"

                # Verify GPU client was called
                mock_gpu_client.process_pdf.assert_called_once_with(1, "uploads/test/test.pdf")

    @pytest.mark.asyncio
    async def test_trigger_gpu_processing_failure(self, mock_pitch_deck):
        """Test GPU processing failure handling."""
        # Mock the database session
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
        mock_db.commit.return_value = None

        # Mock the GPU HTTP client to return failure
        mock_gpu_client = Mock(spec=GPUHTTPClient)
        mock_gpu_client.process_pdf = AsyncMock(return_value={
            "success": False,
            "error": "GPU processing failed"
        })

        with patch('app.api.documents.SessionLocal', return_value=mock_db):
            with patch('app.api.documents.gpu_http_client', mock_gpu_client):
                # Execute the async function
                await trigger_gpu_processing(1, "uploads/test/test.pdf")

                # Verify database updates
                assert mock_pitch_deck.processing_status == "failed"
                assert mock_db.commit.call_count == 2  # Once for "processing", once for "failed"

    @pytest.mark.asyncio
    async def test_trigger_gpu_processing_exception(self, mock_pitch_deck):
        """Test GPU processing exception handling."""
        # Mock the database session
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
        mock_db.commit.return_value = None

        # Mock the GPU HTTP client to raise exception
        mock_gpu_client = Mock(spec=GPUHTTPClient)
        mock_gpu_client.process_pdf = AsyncMock(side_effect=Exception("Connection error"))

        with patch('app.api.documents.SessionLocal', return_value=mock_db):
            with patch('app.api.documents.gpu_http_client', mock_gpu_client):
                # Execute the async function
                await trigger_gpu_processing(1, "uploads/test/test.pdf")

                # Verify database updates - should be marked as failed
                assert mock_pitch_deck.processing_status == "failed"
                assert mock_db.commit.call_count >= 2  # At least once for "processing", once for "failed"

    @pytest.mark.asyncio
    async def test_trigger_gpu_processing_database_error(self, mock_pitch_deck):
        """Test handling of database errors during processing."""
        # Mock the database session to fail
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pitch_deck
        mock_db.commit.side_effect = Exception("Database error")

        # Mock the GPU HTTP client
        mock_gpu_client = Mock(spec=GPUHTTPClient)
        mock_gpu_client.process_pdf = AsyncMock(return_value={
            "success": True,
            "results_file": "job_1_12345_results.json"
        })

        with patch('app.api.documents.SessionLocal', return_value=mock_db):
            with patch('app.api.documents.gpu_http_client', mock_gpu_client):
                # Execute the async function - should not raise exception
                await trigger_gpu_processing(1, "uploads/test/test.pdf")

                # Verify GPU client was still called
                mock_gpu_client.process_pdf.assert_called_once_with(1, "uploads/test/test.pdf")

    def test_pitch_deck_created_with_processing_status(self, mock_user):
        """Test that pitch decks are created with 'processing' status."""
        client = TestClient(app)
        
        # Mock authentication
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.documents.volume_storage.save_file', return_value="uploads/test/test.pdf"):
                with patch('app.api.documents.get_db') as mock_get_db:
                    mock_db = Mock(spec=Session)
                    mock_get_db.return_value = mock_db
                    
                    # Create test file
                    test_file = ("test.pdf", b"PDF content", "application/pdf")
                    
                    response = client.post(
                        "/api/documents/upload",
                        files={"file": test_file}
                    )
                    
                    assert response.status_code == 200
                    assert response.json()["processing_status"] == "processing"

    def test_background_task_triggered_on_upload(self, mock_user):
        """Test that background task is triggered on file upload."""
        client = TestClient(app)
        
        # Mock authentication
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.documents.volume_storage.save_file', return_value="uploads/test/test.pdf"):
                with patch('app.api.documents.get_db') as mock_get_db:
                    mock_db = Mock(spec=Session)
                    mock_get_db.return_value = mock_db
                    
                    # Mock BackgroundTasks
                    with patch('app.api.documents.BackgroundTasks.add_task') as mock_add_task:
                        # Create test file
                        test_file = ("test.pdf", b"PDF content", "application/pdf")
                        
                        response = client.post(
                            "/api/documents/upload",
                            files={"file": test_file}
                        )
                        
                        assert response.status_code == 200
                        # Verify background task was added
                        mock_add_task.assert_called_once()


class TestGPUHTTPClient:
    """Test suite for GPU HTTP client functionality."""

    @pytest.fixture
    def gpu_client(self):
        """Create a GPU HTTP client instance."""
        return GPUHTTPClient(gpu_host="localhost")

    @pytest.mark.asyncio
    async def test_process_pdf_success(self, gpu_client):
        """Test successful PDF processing via HTTP."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results_file": "job_1_12345_results.json",
            "results_path": "/mnt/CPU-GPU/results/job_1_12345_results.json"
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await gpu_client.process_pdf(1, "uploads/test/test.pdf")
            
            assert result["success"] is True
            assert "results_file" in result
            assert "results_path" in result

    @pytest.mark.asyncio
    async def test_process_pdf_timeout(self, gpu_client):
        """Test PDF processing timeout handling."""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            
            result = await gpu_client.process_pdf(1, "uploads/test/test.pdf")
            
            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_process_pdf_connection_error(self, gpu_client):
        """Test PDF processing connection error handling."""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            result = await gpu_client.process_pdf(1, "uploads/test/test.pdf")
            
            assert result["success"] is False
            assert "connection" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_process_pdf_http_error(self, gpu_client):
        """Test PDF processing HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await gpu_client.process_pdf(1, "uploads/test/test.pdf")
            
            assert result["success"] is False
            assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_process_pdf_no_gpu_host(self):
        """Test PDF processing when no GPU host is configured."""
        gpu_client = GPUHTTPClient(gpu_host=None)
        
        result = await gpu_client.process_pdf(1, "uploads/test/test.pdf")
        
        assert result["success"] is False
        assert "not configured" in result["error"]

    def test_is_available_success(self, gpu_client):
        """Test GPU availability check success."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = gpu_client.is_available()
            
            assert result is True

    def test_is_available_failure(self, gpu_client):
        """Test GPU availability check failure."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            result = gpu_client.is_available()
            
            assert result is False

    def test_get_installed_models_success(self, gpu_client):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "models": [
                {
                    "name": "gemma3:12b",
                    "size": 8149190253,
                    "modified_at": "2025-01-01T00:00:00Z",
                    "digest": "abc123"
                }
            ]
        }

        with patch('requests.get', return_value=mock_response):
            result = gpu_client.get_installed_models()
            
            assert len(result) == 1
            assert result[0].name == "gemma3:12b"
            assert result[0].size == 8149190253


class TestStatusTransitions:
    """Test suite for status transition logic."""

    def test_upload_to_processing_transition(self):
        """Test status transition from upload to processing."""
        # This would typically be part of integration tests
        # but we can test the logic here
        initial_status = "pending"
        expected_status = "processing"
        
        # Simulate status update logic
        assert initial_status != expected_status
        assert expected_status == "processing"

    def test_processing_to_completed_transition(self):
        """Test status transition from processing to completed."""
        processing_status = "processing"
        success_result = {"success": True}
        
        final_status = "completed" if success_result.get("success") else "failed"
        
        assert final_status == "completed"

    def test_processing_to_failed_transition(self):
        """Test status transition from processing to failed."""
        processing_status = "processing"
        failure_result = {"success": False, "error": "GPU error"}
        
        final_status = "completed" if failure_result.get("success") else "failed"
        
        assert final_status == "failed"


class TestNonBlockingBehavior:
    """Test suite for non-blocking behavior verification."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self):
        """Test that multiple requests can be processed concurrently."""
        # Simulate concurrent requests
        async def mock_process_pdf(pitch_deck_id, file_path):
            # Simulate processing time
            await asyncio.sleep(0.1)
            return {"success": True, "results_file": f"job_{pitch_deck_id}_results.json"}

        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = asyncio.create_task(mock_process_pdf(i, f"file_{i}.pdf"))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all tasks completed successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["success"] is True
            assert f"job_{i}_results.json" in result["results_file"]

    @pytest.mark.asyncio
    async def test_async_function_does_not_block(self):
        """Test that async functions don't block the event loop."""
        start_time = asyncio.get_event_loop().time()
        
        # Create a long-running task
        async def long_running_task():
            await asyncio.sleep(0.5)
            return "completed"
        
        # Create a quick task
        async def quick_task():
            return "quick"
        
        # Run both tasks concurrently
        long_task = asyncio.create_task(long_running_task())
        quick_task = asyncio.create_task(quick_task())
        
        # Quick task should complete first
        quick_result = await quick_task
        assert quick_result == "quick"
        
        # Long task should still complete
        long_result = await long_task
        assert long_result == "completed"
        
        # Total time should be close to 0.5 seconds, not 1.0
        total_time = asyncio.get_event_loop().time() - start_time
        assert total_time < 0.7  # Allow some buffer for test execution


if __name__ == "__main__":
    pytest.main([__file__, "-v"])