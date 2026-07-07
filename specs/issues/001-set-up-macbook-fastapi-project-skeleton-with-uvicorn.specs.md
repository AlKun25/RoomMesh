# Technical Specification for Issue #1

## Issue Summary

- **Title**: Set up MacBook FastAPI project skeleton with uvicorn
- **Number**: #1
- **State**: OPEN
- **Labels**:
  - phase:0-foundations (Blocking, foundational work)
  - type:infra (Scaffolding, wiring, setup work)
  - priority:high (Blocking, early phase work)

## Problem Statement

The RoomMesh project requires a foundational FastAPI application that will serve as the base for future phases of development. The project needs:

1. A proper project structure that separates concerns (signaling, scene serving, shared configuration)
2. A health check endpoint for basic server status verification
3. Environment and configuration management for reusable values (e.g., scans directory path)
4. The ability to run the application locally with uvicorn

This sets the groundwork for all subsequent development phases.

## Technical Approach

### Project Structure

Create a modular FastAPI application with the following structure:

```
src/
├── __init__.py
├── main.py                          # Application entry point
├── config.py                        # Configuration and environment handling
└── modules/
    ├── __init__.py
    ├── signaling/                   # Signaling module (for future expansion)
    │   └── __init__.py
    ├── scene/                       # Scene serving module (for future expansion)
    │   └── __init__.py
    └── health/                      # Health check endpoint
        ├── __init__.py
        └── routes.py
```

### Configuration Management

- Use Pydantic's `BaseSettings` (or `pydantic.settings.BaseSettings`) for environment variable handling
- Store configuration in a `config.py` module
- Load environment variables for:
  - `SCANS_DIR`: Path to scans directory (default: `./scans`)
  - `HOST`: Server host (default: `127.0.0.1`)
  - `PORT`: Server port (default: `8000`)
  - `DEBUG`: Debug mode flag (default: `false`)

### Health Check Endpoint

- Implement `GET /health` endpoint
- Return JSON response with:
  - `status`: "healthy" or "degraded"
  - `timestamp`: ISO format timestamp
  - `version`: Application version from `__init__.py`

### FastAPI Application

- Initialize FastAPI app in `main.py`
- Include health check router
- Set up error handlers for proper error responses
- Configure CORS if needed for future phases

## Implementation Plan

1. **Setup Configuration Module** (`src/config.py`)
   - Import Pydantic's `BaseSettings` or use `pydantic_settings`
   - Define `Settings` class with environment variables
   - Create settings instance for app-wide use

2. **Create Module Structure** (`src/modules/`)
   - Create `signaling/`, `scene/`, and `health/` packages
   - Add `__init__.py` files to each module

3. **Implement Health Check** (`src/modules/health/routes.py`)
   - Create FastAPI router
   - Implement `/health` endpoint that returns status JSON

4. **Update Main Application** (`src/main.py`)
   - Import FastAPI and create app instance
   - Include configuration
   - Register health check router
   - Add uvicorn run logic if running as `__main__`

5. **Update Dependencies** (`pyproject.toml`)
   - Add `fastapi>=0.100.0`
   - Add `uvicorn[standard]>=0.24.0`
   - Add `pydantic-settings>=2.0.0`

6. **Create `.env.example`**
   - Document expected environment variables
   - Provide default values

## Test Plan

1. **Unit Tests** (`tests/test_config.py`):
   - Test configuration loading from environment variables
   - Test default values
   - Test validation of invalid configurations

2. **Integration Tests** (`tests/test_health.py`):
   - Test GET `/health` returns 200 status
   - Test response contains required fields (`status`, `timestamp`, `version`)
   - Test response structure matches expected JSON schema

3. **Application Tests** (`tests/test_main.py`):
   - Test app starts without errors
   - Test app can be imported and instantiated
   - Test all routers are properly registered

4. **Manual Testing**:
   - Run `uvicorn src.main:app --reload` and verify it starts
   - Call `curl http://localhost:8000/health` and verify response
   - Test with environment variables set and unset

## Files to Modify

- **`pyproject.toml`**: Add FastAPI, uvicorn, and pydantic-settings dependencies

## Files to Create

- **`src/main.py`**: FastAPI application entry point
- **`src/config.py`**: Configuration and settings management
- **`src/modules/__init__.py`**: Modules package marker
- **`src/modules/signaling/__init__.py`**: Signaling module (placeholder)
- **`src/modules/scene/__init__.py`**: Scene serving module (placeholder)
- **`src/modules/health/__init__.py`**: Health module marker
- **`src/modules/health/routes.py`**: Health check endpoint router
- **`.env.example`**: Example environment variables
- **`tests/__init__.py`**: Tests package marker
- **`tests/test_main.py`**: Application tests
- **`tests/test_config.py`**: Configuration tests
- **`tests/test_health.py`**: Health endpoint tests

## Existing Utilities to Leverage

- **`src/__init__.py`**: Already exists with version string (update if version changes)
- **`pyproject.toml`**: Existing configuration file (add dependencies)
- **`ruff`**: Already configured for linting/formatting (run before commits)

## Success Criteria

- [ ] FastAPI application starts with `uvicorn src.main:app --reload` without errors
- [ ] `GET /health` endpoint returns 200 status code
- [ ] Health endpoint response includes `status`, `timestamp`, and `version` fields
- [ ] Configuration loads from environment variables with proper defaults
- [ ] Application can be imported in Python: `from src.main import app`
- [ ] Module structure follows planned layout (signaling, scene, health)
- [ ] All code passes ruff linting and formatting checks
- [ ] Basic unit and integration tests exist and pass

## Out of Scope

- **Signaling functionality**: Signaling module is a placeholder for future phases
- **Scene serving**: Scene serving module is a placeholder for future phases
- **Authentication/Authorization**: Not needed for initial health check
- **Database integration**: Deferred to later phases
- **Advanced monitoring**: Only basic health status required
- **Production deployment configuration**: Focus on local development setup
- **Comprehensive test coverage**: Minimum viable tests for core functionality

## Technical Notes

- Use Python 3.13+ as specified in `pyproject.toml`
- Follow PEP 8 naming conventions enforced by Ruff
- Keep modules small and focused (under 300 lines per file)
- Use async/await for FastAPI endpoints to enable future scalability
- Keep configuration module independent and testable
