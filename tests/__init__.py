"""Modular, non-tautological TDD test suite for Castalia (D2R Overhaul Mod)."""
import os
import sys

TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
