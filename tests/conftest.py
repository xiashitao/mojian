"""
Shared pytest fixtures.
"""
import sys
import os

# Make bazibase importable when running from the bazibase/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
