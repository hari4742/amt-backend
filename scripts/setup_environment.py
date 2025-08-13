#!/usr/bin/env python3
"""
Environment setup script for AMT Backend.
This script helps set up the environment and checks for common issues.
"""

import os
import sys
import platform
from pathlib import Path


def check_redis_connection():
    """Check if Redis is available."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
        r.ping()
        print("✓ Redis connection successful")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("  Please make sure Redis is running on localhost:6379")
        return False


def check_environment_file():
    """Check if .env file exists and create one if needed."""
    env_file = Path(".env")
    env_example = Path("env.example")

    if env_file.exists():
        print("✓ .env file exists")
        return True

    if env_example.exists():
        print("! .env file not found, but env.example exists")
        print("  Please copy env.example to .env and configure it:")
        print("  cp env.example .env")
        return False

    print("✗ Neither .env nor env.example found")
    return False


def check_windows_compatibility():
    """Check Windows-specific compatibility issues."""
    if platform.system() == "Windows":
        print("✓ Running on Windows")
        print("  Note: Using thread pool for Celery workers")
        print("  Use start_celery_worker.bat to start workers")
        return True
    else:
        print("✓ Running on non-Windows platform")
        return True


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        ('celery', 'celery'),
        ('redis', 'redis'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('pydantic', 'pydantic'),
        ('pydantic-settings', 'pydantic_settings'),
        ('python-dotenv', 'dotenv')
    ]

    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            print(f"✗ {package_name} - not installed")
            missing_packages.append(package_name)

    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r requirements.txt")
        return False

    return True


def main():
    """Main setup function."""
    print("AMT Backend Environment Setup")
    print("=" * 40)

    checks = [
        ("Environment File", check_environment_file),
        ("Dependencies", check_dependencies),
        ("Redis Connection", check_redis_connection),
        ("Platform Compatibility", check_windows_compatibility),
    ]

    all_passed = True
    for name, check_func in checks:
        print(f"\n{name}:")
        if not check_func():
            all_passed = False

    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All checks passed! Your environment is ready.")
        print("\nTo start the application:")
        print("1. Start Redis server")
        print("2. Run: python -m uvicorn app.main:app --reload")
        print("3. For Celery workers on Windows: run start_celery_worker.bat")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
