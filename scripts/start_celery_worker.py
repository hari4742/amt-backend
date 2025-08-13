#!/usr/bin/env python3
"""
Windows-compatible Celery worker startup script.
This script handles Windows-specific issues with Celery.
"""

import os
import sys
import platform
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Start Celery worker with Windows-compatible settings."""

    if platform.system() != "Windows":
        print("This script is designed for Windows. Use regular Celery commands on other platforms.")
        sys.exit(1)

    # Set Windows-specific environment variables
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

    # Import after setting environment
    from app.core.celery_app import celery_app

    # Start the worker with Windows-compatible settings
    argv = [
        'worker',
        '--loglevel=info',
        '--pool=threads',  # Use threads instead of processes on Windows
        '--concurrency=4',  # Limit concurrency to avoid issues
        '--without-gossip',  # Disable gossip to reduce complexity
        '--without-mingle',  # Disable mingle to reduce complexity
        '--without-heartbeat',  # Disable heartbeat to reduce complexity
    ]

    celery_app.worker_main(argv)


if __name__ == '__main__':
    main()
