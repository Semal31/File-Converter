# Testing Patterns

**Analysis Date:** 2026-02-24

## Test Framework

**Status:** Not Implemented

**Observation:** The codebase has no test files, no test framework configured, and no testing infrastructure in place.

- No `pytest.ini`, `pyproject.toml` with pytest config, or `conftest.py`
- No test files found matching patterns: `test_*.py`, `*_test.py`, `tests/` directory
- No `unittest` or `pytest` imports in any module
- No GitHub Actions workflow for testing (only Docker build)
- No test dependencies in `requirements.txt`

## Testing Approach Required

Given the absence of testing, the following is a recommended approach based on codebase structure:

### Test Framework Recommendation

**Use pytest** with the following configuration:

```toml
# Add to pyproject.toml or create pytest.ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
minversion = "7.0"
```

**Test dependencies to add to `requirements.txt`:**
```
pytest>=7.0.0
pytest-asyncio>=0.21.0    # For async test support
pytest-mock>=3.10.0       # For mocking
httpx>=0.25.0             # For testing FastAPI
```

## Test File Organization

**Recommended Location:**
- Primary location: `tests/` directory at project root (sibling to `backend/`)
- Structure mirrors `backend/` structure: `tests/converters/`, `tests/test_main.py`

**Naming Convention:**
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test{ModuleName}` (e.g., `TestImageConverter`, `TestAudioConverter`)
- Test functions: `test_{feature_being_tested}` (e.g., `test_convert_jpg_to_png`)

**Directory Structure:**
```
tests/
├── conftest.py                    # Shared fixtures
├── test_main.py                   # FastAPI endpoint tests
├── test_format_detection.py       # Format detection tests
└── converters/
    ├── test_base.py               # BaseConverter interface tests
    ├── test_images.py             # ImageConverter tests
    ├── test_audio.py              # AudioConverter tests
    ├── test_video.py              # VideoConverter tests
    ├── test_documents.py          # DocumentConverter tests
    ├── test_data.py               # DataConverter tests
    └── test_archives.py           # ArchiveConverter tests
```

## Test Structure Pattern

**Recommended pytest structure with async support:**

```python
# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test /api/health endpoint."""

    def test_health_returns_ok(self, client):
        """Health check should return ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "1.0.0"}


class TestUploadEndpoint:
    """Test /api/upload endpoint."""

    def test_upload_valid_file(self, client, tmp_path):
        """Uploading a valid file should return metadata."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.txt", f, "text/plain")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["filename"] == "test.txt"
        assert data["detected_format"] == "txt"

    def test_upload_unsupported_format(self, client, tmp_path):
        """Uploading unsupported format should return 400."""
        test_file = tmp_path / "test.unknown"
        test_file.write_bytes(b"binary")

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.unknown", f, "application/octet-stream")}
            )

        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]
```

## Async Testing

**Pattern for async converter tests:**

```python
# tests/converters/test_images.py
import pytest
from pathlib import Path
from backend.converters.images import ImageConverter


@pytest.fixture
async def image_converter():
    """Create ImageConverter instance."""
    return ImageConverter()


@pytest.mark.asyncio
async def test_convert_jpg_to_png(image_converter, tmp_path):
    """Converting JPG to PNG should succeed."""
    # Setup test image (use PIL to create minimal test image)
    from PIL import Image

    input_file = tmp_path / "test.jpg"
    output_file = tmp_path / "test.png"

    # Create minimal JPEG
    img = Image.new("RGB", (10, 10), color="red")
    img.save(input_file, "JPEG")

    # Perform conversion
    await image_converter.convert(
        input_path=input_file,
        input_format="jpg",
        output_format="png",
        output_path=output_file
    )

    # Assert output exists and is valid PNG
    assert output_file.exists()
    png_check = Image.open(output_file)
    assert png_check.format == "PNG"
```

## Mocking

**Framework:** pytest-mock (use `mocker` fixture)

**When to Mock:**
- External system calls: `ffprobe`, `ffmpeg`, `pandoc` subprocess calls
- File I/O intensive operations where test data would be large
- Network calls (if any added in future)
- Expensive operations (audio/video probing)

**When NOT to Mock:**
- Core converter logic (image transforms, data format parsing)
- Format detection (should use real file samples)
- Error handling paths
- BusinessLogic/algorithm correctness

**Example Mocking Pattern:**

```python
# tests/converters/test_audio.py
@pytest.mark.asyncio
async def test_audio_quality_original_detects_bitrate(mocker, audio_converter, tmp_path):
    """When quality='original', bitrate should be detected from source."""
    # Mock ffprobe to return known bitrate
    mock_probe = mocker.patch('ffmpeg.probe')
    mock_probe.return_value = {
        "streams": [{"codec_type": "audio", "bit_rate": "192000"}],
        "format": {}
    }

    input_file = tmp_path / "test.mp3"
    output_file = tmp_path / "test.ogg"
    input_file.write_bytes(b"fake mp3")

    # Mock pydub to avoid actual conversion
    mock_segment = mocker.patch('pydub.AudioSegment.from_file')
    mock_audio = mocker.MagicMock()
    mock_segment.return_value = mock_audio

    await audio_converter.convert(
        input_path=input_file,
        input_format="mp3",
        output_format="ogg",
        output_path=output_file,
        quality="original"
    )

    # Assert export was called with correct quality settings
    mock_audio.export.assert_called_once()
    call_kwargs = mock_audio.export.call_args[1]
    assert "parameters" in call_kwargs  # OGG quality parameters
```

## Fixtures and Test Data

**Shared fixtures in `tests/conftest.py`:**

```python
# tests/conftest.py
import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir):
    """Create minimal valid test files for each format."""
    files = {}

    # Create text file
    txt_file = temp_dir / "test.txt"
    txt_file.write_text("Test content")
    files["txt"] = txt_file

    # Create JSON file
    json_file = temp_dir / "test.json"
    json_file.write_text('{"key": "value"}')
    files["json"] = json_file

    # Create image files using PIL
    from PIL import Image
    for fmt, pil_fmt in [("jpg", "JPEG"), ("png", "PNG"), ("bmp", "BMP")]:
        img = Image.new("RGB", (10, 10), color="blue")
        img_file = temp_dir / f"test.{fmt}"
        img.save(img_file, pil_fmt)
        files[fmt] = img_file

    return files
```

**Using fixtures in tests:**

```python
def test_detect_format_identifies_json(sample_files):
    """Format detection should correctly identify JSON."""
    from backend.converters import detect_format

    fmt, category = detect_format(str(sample_files["json"]))
    assert fmt == "json"
    assert category == "data"
```

## Error Testing

**Pattern for testing error conditions:**

```python
# tests/converters/test_images.py
class TestImageConverterErrors:
    """Test error handling in ImageConverter."""

    @pytest.mark.asyncio
    async def test_convert_from_unsupported_format_raises_error(self, image_converter, tmp_path):
        """Converting from unsupported format should raise ValueError."""
        input_file = tmp_path / "test.txt"
        output_file = tmp_path / "test.png"
        input_file.write_text("not an image")

        with pytest.raises(ValueError, match="Cannot.*format"):
            await image_converter.convert(
                input_path=input_file,
                input_format="unknown",
                output_format="png",
                output_path=output_file
            )

    @pytest.mark.asyncio
    async def test_convert_corrupted_image_raises_error(self, image_converter, tmp_path):
        """Converting corrupted image should raise PIL error."""
        input_file = tmp_path / "corrupted.jpg"
        output_file = tmp_path / "test.png"
        input_file.write_bytes(b"not a real jpeg")

        with pytest.raises(Exception):  # PIL.UnidentifiedImageError
            await image_converter.convert(
                input_path=input_file,
                input_format="jpg",
                output_format="png",
                output_path=output_file
            )


# tests/test_format_detection.py
class TestFormatDetection:
    """Test format detection edge cases."""

    def test_detect_format_tar_gz(self):
        """Should correctly detect tar.gz compound extension."""
        from backend.converters import detect_format

        fmt, category = detect_format("archive.tar.gz")
        assert fmt == "tar.gz"
        assert category == "archive"

    def test_detect_format_missing_extension_raises_error(self):
        """File without extension should raise ValueError."""
        from backend.converters import detect_format

        with pytest.raises(ValueError, match="no file extension"):
            detect_format("no_extension")

    def test_detect_format_unsupported_extension_raises_error(self):
        """Unsupported extension should raise ValueError."""
        from backend.converters import detect_format

        with pytest.raises(ValueError, match="Unsupported format"):
            detect_format("file.xyz")
```

## Coverage Recommendations

**Coverage Target:** Aim for 80%+ coverage for critical paths

**High Priority (must test):**
- Format detection: `converters/__init__.py` (detect_format, get_available_formats)
- Converter interfaces: `converters/base.py`
- API endpoints: `main.py` (upload, convert, download, bulk operations)
- Error handling: All exception paths

**Medium Priority (should test):**
- Individual converter implementations (representative sample of each type)
- Quality preset selection logic (audio.py bitrate selection, video.py CRF selection)
- Archive extraction/packing (security implications for zip path traversal)

**Lower Priority (can skip initially):**
- External dependency behavior (ffmpeg, pandoc actual execution)
- Temporary file cleanup (hard to test without mocking)
- Specific format edge cases (defer to real integration tests)

**Generate Coverage Report:**

```bash
# Run pytest with coverage
pytest --cov=backend --cov-report=html tests/

# View coverage in htmlcov/index.html
```

## Recommended Test Execution Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_main.py -v

# Run specific test class
pytest tests/converters/test_images.py::TestImageConverter -v

# Run with coverage
pytest --cov=backend tests/

# Run in watch mode (requires pytest-watch)
ptw tests/

# Run async tests with proper plugin
pytest --asyncio-mode=auto tests/
```

## Missing Test Infrastructure

**Not Currently Present:**
- No `conftest.py` for shared fixtures
- No sample test files or test data directory
- No mock/stub implementations
- No CI/CD testing step (only Docker build in GitHub Actions)
- No pre-commit hooks for test validation
- No coverage threshold enforcement

**First Steps to Add Testing:**
1. Install pytest and dependencies in `requirements.txt` (dev section)
2. Create `tests/conftest.py` with shared fixtures
3. Write tests for `converters/__init__.py` (format detection is critical)
4. Write integration tests for main API endpoints
5. Add pytest to GitHub Actions workflow before Docker build

---

*Testing analysis: 2026-02-24*
