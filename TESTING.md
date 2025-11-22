# Testing Guide

Comprehensive guide for testing the Slack Listener application.

## Quick Start

```bash
# Install test dependencies
make install-dev

# Run all tests
make test

# Run with coverage
make test-cov
```

## Test Suite Overview

The application has **comprehensive test coverage** including:

- ✅ **Unit Tests**: Individual component testing
- ✅ **Integration Tests**: End-to-end workflow testing
- ✅ **Vision/Image Tests**: Complete image processing pipeline
- ✅ **Mock Testing**: Slack and AWS Bedrock mocking
- ✅ **Error Handling**: Edge cases and failure scenarios

## Running Tests

### All Tests

```bash
make test
# or
pytest
```

### Unit Tests Only

```bash
make test-unit
# or
pytest tests/unit -v
```

### Integration Tests Only

```bash
make test-integration
# or
pytest tests/integration -v
```

### With Coverage Report

```bash
make test-cov
# or
pytest --cov=src --cov-report=html --cov-report=term
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Specific Test File

```bash
pytest tests/unit/test_bedrock_client.py -v
```

### Specific Test Function

```bash
pytest tests/unit/test_bedrock_client.py::test_invoke_claude_success -v
```

### Run Tests Matching Pattern

```bash
pytest -k "vision" -v  # All tests with "vision" in the name
pytest -k "image" -v   # All tests with "image" in the name
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                        # Shared fixtures and configuration
├── unit/                              # Unit tests
│   ├── __init__.py
│   ├── test_config.py                 # Configuration loading/validation
│   ├── test_bedrock_client.py         # AWS Bedrock client
│   ├── test_slack_helpers.py          # Slack utilities
│   ├── test_message_handler.py        # Message handling logic
│   └── test_command_handler.py        # Slash command handling
└── integration/                       # Integration tests
    ├── __init__.py
    └── test_vision_integration.py     # Complete vision workflow
```

## Key Test Areas

### 1. Configuration Tests (`test_config.py`)

- YAML file loading
- Pydantic validation
- Channel and command lookup
- Default values
- Error handling for invalid configs

```bash
pytest tests/unit/test_config.py -v
```

### 2. Bedrock Client Tests (`test_bedrock_client.py`)

- Message formatting
- Image encoding (base64)
- MIME type preservation (PNG, JPEG, WebP, GIF)
- API invocation
- Error handling
- Response parsing

**Key Vision Tests:**
- `test_format_message_with_image`: Single image formatting
- `test_format_message_multiple_images`: Multiple images
- `test_image_mimetype_preservation`: MIME type handling

```bash
pytest tests/unit/test_bedrock_client.py -v
```

### 3. Slack Helpers Tests (`test_slack_helpers.py`)

- Keyword matching (case-sensitive/insensitive)
- File downloads from Slack
- Image extraction from messages
- Message filtering (bots, self, system messages)
- Text formatting and truncation

**Key Vision Tests:**
- `test_extract_message_images_success`: Image download and extraction
- `test_extract_message_images_multiple_formats`: PNG, JPEG, WebP support

```bash
pytest tests/unit/test_slack_helpers.py -v
```

### 4. Message Handler Tests (`test_message_handler.py`)

- Keyword-triggered responses
- Image message handling
- Bot/self message filtering
- Thread replies
- Reaction addition
- Error handling

```bash
pytest tests/unit/test_message_handler.py -v
```

### 5. Command Handler Tests (`test_command_handler.py`)

- Slash command parsing
- Response generation
- Error messages
- Parameter validation

```bash
pytest tests/unit/test_command_handler.py -v
```

### 6. Vision Integration Tests (`test_vision_integration.py`)

**Complete end-to-end vision workflow:**

1. Slack message with image arrives
2. Image is downloaded from Slack
3. Image is base64 encoded with correct MIME type
4. Message sent to Bedrock with image data
5. Claude analyzes the image
6. Response posted back to Slack in thread

```bash
pytest tests/integration/test_vision_integration.py -v
```

**Key Tests:**
- `test_complete_image_workflow`: Full Slack → Bedrock → Slack flow
- `test_multiple_images_workflow`: Multiple images in one message
- `test_vision_error_handling`: Graceful error handling

## Understanding Fixtures

Fixtures provide reusable test data and mocks. Key fixtures in `conftest.py`:

### Configuration Fixtures

```python
@pytest.fixture
def sample_bedrock_config():
    """Bedrock configuration for testing."""

@pytest.fixture
def sample_channel_config():
    """Channel configuration for testing."""

@pytest.fixture
def sample_image_channel_config():
    """Image analysis channel configuration."""
```

### Mock Fixtures

```python
@pytest.fixture
def mock_slack_app():
    """Mock Slack Bolt application."""

@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client with canned responses."""
```

### Test Data Fixtures

```python
@pytest.fixture
def sample_image_bytes():
    """1x1 red pixel PNG for testing."""

@pytest.fixture
def sample_image_info():
    """Image data with MIME type and filename."""

@pytest.fixture
def mock_bedrock_vision_response():
    """Mock successful vision API response."""
```

## Writing New Tests

### 1. Create Test File

```python
# tests/unit/test_my_feature.py
"""Tests for my new feature."""

import pytest
from src.my_module import MyFeature


class TestMyFeature:
    """Tests for MyFeature class."""

    def test_basic_functionality(self):
        """Test basic use case."""
        feature = MyFeature()
        result = feature.do_something()
        assert result == expected_value

    def test_error_handling(self):
        """Test error cases."""
        feature = MyFeature()
        with pytest.raises(ValueError):
            feature.do_something_invalid()
```

### 2. Use Existing Fixtures

```python
def test_with_config(sample_app_config):
    """Test using shared config fixture."""
    assert len(sample_app_config.channels) > 0
```

### 3. Create Custom Fixtures

```python
@pytest.fixture
def my_custom_fixture():
    """My custom test data."""
    return {"key": "value"}

def test_with_custom_fixture(my_custom_fixture):
    """Test using custom fixture."""
    assert my_custom_fixture["key"] == "value"
```

### 4. Test Vision Features

```python
def test_image_processing(sample_image_info, mock_bedrock_client):
    """Test image processing."""
    from src.services.bedrock_client import BedrockClient

    client = BedrockClient()
    message = client.format_message("Analyze this", images=[sample_image_info])

    # Verify image content
    assert message["content"][0]["type"] == "image"
    assert message["content"][0]["source"]["media_type"] == "image/png"
```

## Mocking

### Mocking AWS Bedrock

```python
from unittest.mock import patch, MagicMock

@patch("src.services.bedrock_client.boto3")
def test_with_bedrock_mock(mock_boto3):
    """Test with mocked Bedrock."""
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {
        "body": Mock(read=Mock(return_value=b'{"content": [{"text": "Response"}]}'))
    }
    mock_boto3.client.return_value = mock_client

    # Your test code here
```

### Mocking Slack

```python
from unittest.mock import Mock

def test_with_slack_mock():
    """Test with mocked Slack client."""
    say = Mock()
    client = Mock()

    # Call your handler
    handler.handle_message(event, say, client)

    # Verify interactions
    say.assert_called_once()
    client.reactions_add.assert_called()
```

### Mocking HTTP Requests (Slack File Downloads)

```python
import responses

@responses.activate
def test_file_download():
    """Test file download with mocked HTTP."""
    url = "https://files.slack.com/test.png"
    responses.add(responses.GET, url, body=b"fake_image_data", status=200)

    result = download_slack_file(url, "token")
    assert result == b"fake_image_data"
```

## Test Coverage Goals

Target coverage levels:

- **Overall**: > 80%
- **Core Logic** (handlers, services): > 90%
- **Utilities**: > 85%
- **Config**: > 75%

Check current coverage:
```bash
make test-cov
```

## Continuous Integration

To run tests in CI:

```yaml
# .github/workflows/test.yml example
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

- name: Run tests
  run: pytest --cov=src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Common Issues

### ImportError

If you get import errors:
```bash
# Make sure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Fixture Not Found

Ensure `conftest.py` is in the tests directory and properly imported.

### Slow Tests

Run only fast tests:
```bash
pytest -m "not slow"
```

## Best Practices

1. **Test One Thing**: Each test should verify one specific behavior
2. **Use Fixtures**: Reuse test data via fixtures
3. **Mock External Services**: Don't call real AWS or Slack APIs
4. **Test Edge Cases**: Empty inputs, None values, errors
5. **Descriptive Names**: `test_image_with_png_mimetype_preserves_format`
6. **AAA Pattern**: Arrange, Act, Assert
7. **Document Tests**: Add docstrings explaining what's being tested

## Debugging Tests

### Run with Print Statements

```bash
pytest -s tests/unit/test_bedrock_client.py
```

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### Show Local Variables on Failure

```bash
pytest -l
```

### Verbose Output

```bash
pytest -vv
```

## Next Steps

- Add tests when adding new features
- Maintain >80% code coverage
- Run tests before committing
- Review test failures in CI

For more pytest features: https://docs.pytest.org/
