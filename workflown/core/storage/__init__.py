"""
Storage Module

Provides persistent storage interfaces and implementations.
"""

from .base_storage import BaseStorage, StorageBackend, StorageError
from .filesystem_storage import FilesystemStorage
from .sqlite_storage import SQLiteStorage

__all__ = [
    "BaseStorage",
    "StorageBackend", 
    "StorageError",
    "FilesystemStorage",
    "SQLiteStorage"
]