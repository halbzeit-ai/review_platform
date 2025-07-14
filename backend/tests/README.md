# Backend Test Suite

This directory contains the organized test suite for the backend application.

## Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_services/       # Service layer tests
│   │   ├── __init__.py
│   │   ├── test_email_service.py
│   │   ├── test_i18n_service.py
│   │   └── test_token_service.py
│   └── test_api/            # API endpoint tests
│       ├── __init__.py
│       ├── test_auth.py
│       └── test_decks.py
└── integration/             # Integration tests
    ├── __init__.py
    ├── test_auth_flow.py
    └── test_email_flow.py
```

## Test Types

### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Mock external dependencies
- Fast execution
- High code coverage

### Integration Tests (`tests/integration/`)
- Test component interactions
- Use real or in-memory databases
- Test complete workflows
- End-to-end scenarios

## Running Tests

### Using the Test Runner
```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run with coverage reporting
python run_tests.py --coverage

# Run unit tests with coverage
python run_tests.py --unit --coverage
```

### Using pytest Directly
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_services/test_i18n_service.py

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run tests with specific markers
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "email"
```

## Test Configuration

### pytest.ini
Contains pytest configuration including:
- Test discovery patterns
- Output formatting
- Test markers
- Default options

### conftest.py
Contains shared fixtures and configuration:
- Mock settings
- Database fixtures
- Sample data
- Common mocks

## Test Markers

Use markers to categorize tests:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.email` - Email-related tests
- `@pytest.mark.i18n` - Internationalization tests

## Writing Tests

### Unit Test Example
```python
import pytest
from unittest.mock import patch, MagicMock

from app.services.email_service import EmailService

class TestEmailService:
    def test_send_email_success(self):
        # Arrange
        with patch('app.services.email_service.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            service = EmailService()
            
            # Act
            result = service.send_email("test@example.com", "Subject", "Body")
            
            # Assert
            assert result is True
            mock_server.send_message.assert_called_once()
```

### Integration Test Example
```python
import pytest
from fastapi.testclient import TestClient

from app.main import app

class TestAuthFlow:
    def test_registration_flow(self, client, mock_db):
        # Test complete registration workflow
        response = client.post("/auth/register", json=registration_data)
        assert response.status_code == 200
        # ... additional assertions
```

## Best Practices

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Test Names**: `test_should_send_german_email_when_language_is_de`
3. **One Assertion Per Test**: Focus on single behavior
4. **Mock External Dependencies**: Database, email service, HTTP calls
5. **Use Fixtures**: Share common setup code
6. **Test Edge Cases**: Empty inputs, invalid data, error conditions
7. **Maintain Test Independence**: Tests should not depend on each other

## Coverage Goals

- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: Cover critical user flows
- **Overall**: 85%+ combined coverage

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:
- Fast unit tests for quick feedback
- Integration tests for deployment validation
- Coverage reports for code quality metrics

## Dependencies

Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Required packages:
- pytest: Test framework
- pytest-cov: Coverage reporting
- pytest-mock: Enhanced mocking
- pytest-asyncio: Async test support
- httpx: HTTP client for FastAPI testing