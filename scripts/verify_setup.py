#!/usr/bin/env python3
"""
Verification script for Phase 1 setup.
"""

import os
import sys
import importlib
from pathlib import Path


def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists and print status."""
    exists = os.path.exists(file_path)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {file_path}")
    return exists


def check_directory_exists(dir_path: str, description: str) -> bool:
    """Check if a directory exists and print status."""
    exists = os.path.exists(dir_path)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {dir_path}")
    return exists


def check_import(module_name: str, description: str) -> bool:
    """Check if a module can be imported and print status."""
    try:
        importlib.import_module(module_name)
        print(f"✓ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {description}: {module_name} - {e}")
        return False


def main():
    """Main verification function."""
    print("=" * 60)
    print("AMT Backend - Phase 1 Setup Verification")
    print("=" * 60)

    # Check project structure
    print("\n📁 Project Structure:")
    structure_checks = [
        ("app/__init__.py", "Main app package"),
        ("app/main.py", "FastAPI application"),
        ("app/config.py", "Configuration settings"),
        ("app/core/__init__.py", "Core package"),
        ("app/core/database.py", "Database configuration"),
        ("app/core/celery_app.py", "Celery configuration"),
        ("app/models/__init__.py", "Models package"),
        ("app/models/transcription.py", "Transcription model"),
        ("app/schemas/__init__.py", "Schemas package"),
        ("app/schemas/transcription.py", "Transcription schemas"),
        ("app/api/__init__.py", "API package"),
        ("app/api/v1/__init__.py", "API v1 package"),
        ("app/api/v1/api.py", "API router"),
        ("app/api/v1/endpoints/__init__.py", "Endpoints package"),
        ("app/api/v1/endpoints/transcription.py", "Transcription endpoints"),
        ("app/api/v1/endpoints/health.py", "Health endpoints"),
        ("app/api/v1/endpoints/utils.py", "Utility endpoints"),
        ("app/services/__init__.py", "Services package"),
        ("app/services/transcription_tasks.py", "Transcription tasks"),
        ("app/services/file_service.py", "File service"),
        ("app/services/audio_service.py", "Audio service"),
        ("app/services/midi_service.py", "MIDI service"),
        ("app/services/progress_service.py", "Progress service"),
        ("app/services/monitoring_service.py", "Monitoring service"),
        ("app/services/worker_tasks.py", "Worker tasks"),
        ("app/utils/__init__.py", "Utils package"),
        ("app/utils/file_utils.py", "File utilities"),
        ("app/core/middleware.py", "Middleware"),
        ("app/core/exceptions.py", "Custom exceptions"),
        ("tests/__init__.py", "Tests package"),
        ("tests/conftest.py", "Pytest configuration"),
        ("tests/test_api.py", "API tests"),
        ("tests/test_phase2.py", "Phase 2 tests"),
        ("tests/test_phase3.py", "Phase 3 tests"),
        ("tests/test_phase4.py", "Phase 4 tests"),
    ]

    structure_ok = True
    for file_path, description in structure_checks:
        if not check_file_exists(file_path, description):
            structure_ok = False

    # Check configuration files
    print("\n⚙️  Configuration Files:")
    config_checks = [
        ("requirements.txt", "Python dependencies"),
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker services"),
        ("pyproject.toml", "Development tools"),
        (".flake8", "Linting configuration"),
        ("env.example", "Environment example"),
        (".gitignore", "Git ignore rules"),
        ("README.md", "Project documentation"),
    ]

    config_ok = True
    for file_path, description in config_checks:
        if not check_file_exists(file_path, description):
            config_ok = False

    # Check core imports (basic dependencies)
    print("\n📦 Core Dependencies:")
    core_deps = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("sqlalchemy", "Database ORM"),
        ("celery", "Task queue"),
        ("redis", "Redis client"),
    ]

    deps_ok = True
    for module, description in core_deps:
        if not check_import(module, description):
            deps_ok = False

    # Check application imports
    print("\n🔧 Application Modules:")
    app_modules = [
        ("app.config", "Configuration module"),
        ("app.core.database", "Database module"),
        ("app.core.celery_app", "Celery module"),
        ("app.models.transcription", "Transcription model"),
        ("app.schemas.transcription", "Transcription schemas"),
        ("app.api.v1.endpoints.transcription", "Transcription endpoints"),
        ("app.services.transcription_tasks", "Transcription tasks"),
        ("app.services.file_service", "File service"),
        ("app.services.audio_service", "Audio service"),
        ("app.services.midi_service", "MIDI service"),
        ("app.services.progress_service", "Progress service"),
        ("app.services.monitoring_service", "Monitoring service"),
        ("app.services.worker_tasks", "Worker tasks"),
        ("app.utils.file_utils", "File utilities"),
        ("app.api.v1.endpoints.health", "Health endpoints"),
        ("app.api.v1.endpoints.utils", "Utility endpoints"),
    ]

    app_ok = True
    for module, description in app_modules:
        if not check_import(module, description):
            app_ok = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary:")
    print("=" * 60)

    if structure_ok and config_ok and deps_ok and app_ok:
        print("🎉 All checks passed! Phase 1 setup is complete.")
        print("\nNext steps:")
        print("1. Copy env.example to .env and configure your environment")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Start the application: uvicorn app.main:app --reload")
        print("4. Or use Docker: docker-compose up -d")
        return True
    else:
        print("❌ Some checks failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
