import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask.testing import FlaskClient

from gpu_http_server import GPUHTTPServer, app
from config.processing_config import ProcessingConfig


@pytest.fixture
def test_client():
    """Create a test client for the GPU HTTP server."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = ProcessingConfig()
    config.mount_path = "/tmp/test"
    config.results_path = "/tmp/test/results"
    return config


@pytest.fixture
def mock_pdf_processor():
    """Create a mock PDF processor."""
    processor = Mock()
    processor.process_pdf.return_value = {
        "overall_score": 8.5,
        "analysis": {
            "problem": {"score": 8.0, "analysis": "Good problem identification"},
            "solution": {"score": 9.0, "analysis": "Innovative solution"}
        }
    }
    return processor


class TestGPUHTTPServer:
    """Test suite for GPU HTTP server."""

    def test_server_initialization(self):
        """Test that the GPU HTTP server initializes correctly."""
        server = GPUHTTPServer()
        assert server.app is not None
        assert server.pdf_processor is not None

    def test_health_check_endpoint(self, test_client):
        """Test the health check endpoint."""
        with patch('ollama.list', return_value=[]):
            response = test_client.get('/api/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert data['ollama_available'] is True
            assert 'timestamp' in data

    def test_health_check_ollama_unavailable(self, test_client):
        """Test health check when Ollama is unavailable."""
        with patch('ollama.list', side_effect=Exception("Ollama not available")):
            response = test_client.get('/api/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
            assert data['ollama_available'] is False

    def test_list_models_endpoint(self, test_client):
        """Test the list models endpoint."""
        mock_models = [
            Mock(model='gemma3:12b', size=8149190253, modified_at='2025-01-01T00:00:00Z', digest='abc123'),
            Mock(model='phi4:latest', size=9053116391, modified_at='2025-01-01T01:00:00Z', digest='def456')
        ]
        
        with patch('ollama.list', return_value=mock_models):
            response = test_client.get('/api/models')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['models']) == 2
            assert data['models'][0]['name'] == 'gemma3:12b'
            assert data['models'][1]['name'] == 'phi4:latest'

    def test_list_models_empty(self, test_client):
        """Test listing models when no models are installed."""
        with patch('ollama.list', return_value=[]):
            response = test_client.get('/api/models')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['models']) == 0

    def test_list_models_ollama_error(self, test_client):
        """Test listing models when Ollama returns an error."""
        with patch('ollama.list', side_effect=Exception("Ollama error")):
            response = test_client.get('/api/models')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

    def test_pull_model_endpoint(self, test_client):
        """Test the pull model endpoint."""
        def mock_pull_generator(model_name, stream=True):
            yield {'status': 'downloading'}
            yield {'status': 'complete'}
        
        with patch('ollama.pull', side_effect=mock_pull_generator):
            response = test_client.post('/api/models/gemma3:12b')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'gemma3:12b' in data['message']

    def test_pull_model_missing_name(self, test_client):
        """Test pulling a model without providing a name."""
        response = test_client.post('/api/models/')
        
        assert response.status_code == 404

    def test_pull_model_ollama_error(self, test_client):
        """Test pulling a model when Ollama returns an error."""
        with patch('ollama.pull', side_effect=Exception("Pull failed")):
            response = test_client.post('/api/models/invalid-model')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

    def test_delete_model_endpoint(self, test_client):
        """Test the delete model endpoint."""
        with patch('ollama.delete', return_value=True):
            response = test_client.delete('/api/models/gemma3:12b')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'gemma3:12b' in data['message']

    def test_delete_model_missing_name(self, test_client):
        """Test deleting a model without providing a name."""
        response = test_client.delete('/api/models/')
        
        assert response.status_code == 404

    def test_delete_model_ollama_error(self, test_client):
        """Test deleting a model when Ollama returns an error."""
        with patch('ollama.delete', side_effect=Exception("Delete failed")):
            response = test_client.delete('/api/models/invalid-model')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data


class TestPDFProcessingEndpoint:
    """Test suite for PDF processing endpoint."""

    def test_process_pdf_success(self, test_client, mock_config):
        """Test successful PDF processing."""
        with patch('gpu_http_server.config', mock_config):
            with patch('os.makedirs'):
                with patch('builtins.open', mock_open_for_write()):
                    with patch.object(GPUHTTPServer, 'pdf_processor') as mock_processor:
                        mock_processor.process_pdf.return_value = {
                            "overall_score": 8.5,
                            "analysis": {"problem": {"score": 8.0}}
                        }
                        
                        response = test_client.post('/api/process-pdf', json={
                            "pitch_deck_id": 1,
                            "file_path": "uploads/test/test.pdf"
                        })
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert 'results_file' in data
                        assert 'results_path' in data
                        assert data['results_file'].startswith('job_1_')
                        assert data['results_file'].endswith('_results.json')

    def test_process_pdf_missing_data(self, test_client):
        """Test PDF processing with missing request data."""
        response = test_client.post('/api/process-pdf')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No JSON data provided' in data['error']

    def test_process_pdf_missing_file_path(self, test_client):
        """Test PDF processing with missing file path."""
        response = test_client.post('/api/process-pdf', json={
            "pitch_deck_id": 1
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'file_path is required' in data['error']

    def test_process_pdf_missing_pitch_deck_id(self, test_client):
        """Test PDF processing with missing pitch deck ID."""
        response = test_client.post('/api/process-pdf', json={
            "file_path": "uploads/test/test.pdf"
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'pitch_deck_id is required' in data['error']

    def test_process_pdf_file_not_found(self, test_client, mock_config):
        """Test PDF processing when file doesn't exist."""
        with patch('gpu_http_server.config', mock_config):
            with patch.object(GPUHTTPServer, 'pdf_processor') as mock_processor:
                mock_processor.process_pdf.side_effect = FileNotFoundError("File not found")
                
                response = test_client.post('/api/process-pdf', json={
                    "pitch_deck_id": 1,
                    "file_path": "uploads/test/nonexistent.pdf"
                })
                
                assert response.status_code == 404
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'PDF file not found' in data['error']

    def test_process_pdf_processing_error(self, test_client, mock_config):
        """Test PDF processing when processing fails."""
        with patch('gpu_http_server.config', mock_config):
            with patch.object(GPUHTTPServer, 'pdf_processor') as mock_processor:
                mock_processor.process_pdf.side_effect = Exception("Processing failed")
                
                response = test_client.post('/api/process-pdf', json={
                    "pitch_deck_id": 1,
                    "file_path": "uploads/test/test.pdf"
                })
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'Error processing PDF' in data['error']

    def test_process_pdf_results_file_creation(self, test_client, mock_config):
        """Test that results file is created with correct naming pattern."""
        with patch('gpu_http_server.config', mock_config):
            with patch('os.makedirs') as mock_makedirs:
                with patch('builtins.open', mock_open_for_write()) as mock_open:
                    with patch.object(GPUHTTPServer, 'pdf_processor') as mock_processor:
                        mock_processor.process_pdf.return_value = {"test": "data"}
                        
                        response = test_client.post('/api/process-pdf', json={
                            "pitch_deck_id": 1,
                            "file_path": "uploads/test/test.pdf"
                        })
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        
                        # Verify results directory was created
                        mock_makedirs.assert_called_once()
                        
                        # Verify file was opened for writing
                        mock_open.assert_called_once()
                        
                        # Verify file naming pattern
                        assert data['results_file'].startswith('job_1_')
                        assert data['results_file'].endswith('_results.json')


class TestConfigurationHandling:
    """Test suite for configuration handling."""

    def test_environment_variable_configuration(self):
        """Test that environment variables are loaded correctly."""
        with patch.dict(os.environ, {
            'SHARED_FILESYSTEM_MOUNT_PATH': '/custom/mount',
            'MAX_PROCESSING_TIME': '600',
            'PROCESSING_DEVICE': 'cpu'
        }):
            config = ProcessingConfig.from_env()
            assert config.mount_path == '/custom/mount'
            assert config.max_processing_time == 600
            assert config.device == 'cpu'

    def test_default_configuration_values(self):
        """Test default configuration values."""
        config = ProcessingConfig()
        assert config.mount_path == '/mnt/CPU-GPU'
        assert config.max_processing_time == 300
        assert config.device == 'cuda'

    def test_results_path_property(self):
        """Test results path property."""
        config = ProcessingConfig()
        config.mount_path = '/test/mount'
        
        expected_path = '/test/mount/results'
        assert str(config.results_path) == expected_path

    def test_uploads_path_property(self):
        """Test uploads path property."""
        config = ProcessingConfig()
        config.mount_path = '/test/mount'
        
        expected_path = '/test/mount/uploads'
        assert str(config.uploads_path) == expected_path


class TestErrorHandling:
    """Test suite for error handling."""

    def test_json_parse_error(self, test_client):
        """Test handling of invalid JSON in request."""
        response = test_client.post('/api/process-pdf', 
                                  data='invalid json',
                                  content_type='application/json')
        
        assert response.status_code == 400

    def test_internal_server_error_handling(self, test_client):
        """Test handling of internal server errors."""
        with patch.object(GPUHTTPServer, 'pdf_processor') as mock_processor:
            mock_processor.process_pdf.side_effect = Exception("Unexpected error")
            
            response = test_client.post('/api/process-pdf', json={
                "pitch_deck_id": 1,
                "file_path": "uploads/test/test.pdf"
            })
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

    def test_missing_endpoint_404(self, test_client):
        """Test 404 error for missing endpoints."""
        response = test_client.get('/api/nonexistent')
        
        assert response.status_code == 404


class TestConcurrentRequests:
    """Test suite for concurrent request handling."""

    def test_multiple_health_checks(self, test_client):
        """Test multiple concurrent health checks."""
        with patch('ollama.list', return_value=[]):
            responses = []
            for _ in range(5):
                response = test_client.get('/api/health')
                responses.append(response)
            
            # All responses should be successful
            for response in responses:
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'healthy'

    def test_concurrent_model_operations(self, test_client):
        """Test concurrent model operations."""
        with patch('ollama.list', return_value=[]):
            # Simulate concurrent requests
            responses = []
            for _ in range(3):
                response = test_client.get('/api/models')
                responses.append(response)
            
            # All responses should be successful
            for response in responses:
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True


def mock_open_for_write():
    """Helper function to mock file opening for write operations."""
    from unittest.mock import mock_open
    return mock_open()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])