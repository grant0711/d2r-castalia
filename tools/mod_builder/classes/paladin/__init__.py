"""
paladin/__init__.py
Unified access point for the Paladin 30-skill overhaul.
"""
from . import engine, registry
from .sprites import _build_submenu_skillicon_pair

__all__ = ["engine", "registry", "_build_submenu_skillicon_pair"]
