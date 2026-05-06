"""
Pytest configuration for data-service.
Ensures the project root is in sys.path for imports.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
