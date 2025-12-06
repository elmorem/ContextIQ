"""
Pytest configuration for ContextIQ.

This file is automatically loaded by pytest and sets up the Python path.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
