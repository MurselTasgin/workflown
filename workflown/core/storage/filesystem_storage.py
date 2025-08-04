"""
Filesystem Storage Implementation

File-based storage backend for development and simple deployments.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_storage import BaseStorage, StorageBackend, StorageError, StorageMetadata


class FilesystemStorage(BaseStorage):
    """
    Filesystem-based storage implementation.
    
    Stores data as files in a directory structure.
    Suitable for development and single-node deployments.
    """
    
    def __init__(self, storage_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize filesystem storage.
        
        Args:
            storage_id: Unique identifier
            config: Configuration including 'base_path'
        """
        super().__init__(storage_id, config)
        self.backend_type = StorageBackend.FILESYSTEM
        
        # Get base path from config
        self.base_path = Path(config.get("base_path", "./data") if config else "./data")
        self.create_dirs = config.get("create_dirs", True) if config else True
        
        # Metadata file extension
        self.metadata_ext = ".meta"
    
    async def connect(self) -> None:
        """Connect to filesystem (create directories if needed)."""
        try:
            if self.create_dirs:
                self.base_path.mkdir(parents=True, exist_ok=True)
                
                # Create standard subdirectories
                for subdir in ["workflows", "tasks", "results", "temp"]:
                    (self.base_path / subdir).mkdir(exist_ok=True)
            
            # Check if base path is accessible
            if not self.base_path.exists():
                raise StorageError(f"Base path does not exist: {self.base_path}")
            
            if not os.access(self.base_path, os.R_OK | os.W_OK):
                raise StorageError(f"No read/write access to: {self.base_path}")
            
            self.is_connected = True
            self.last_activity = datetime.now()
            
        except Exception as e:
            raise StorageError(f"Failed to connect to filesystem: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from filesystem."""
        self.is_connected = False
    
    async def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> str:
        """
        Store data to filesystem.
        
        Args:
            key: File path relative to base_path
            data: Data to store
            metadata: Optional metadata
            
        Returns:
            Storage key
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        file_path = self._get_file_path(key)
        
        try:
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write data
            if isinstance(data, (str, bytes)):
                mode = 'w' if isinstance(data, str) else 'wb'
                with open(file_path, mode) as f:
                    f.write(data)
            else:
                # Serialize as JSON
                with open(file_path, 'w') as f:
                    json.dump(data, f, default=self._json_serializer, indent=2)
            
            # Store metadata
            await self._store_metadata(key, data, metadata)
            
            self.last_activity = datetime.now()
            return key
            
        except Exception as e:
            raise StorageError(f"Failed to store {key}: {e}")
    
    async def retrieve(self, key: str) -> Any:
        """
        Retrieve data from filesystem.
        
        Args:
            key: File path relative to base_path
            
        Returns:
            Retrieved data
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            raise StorageError(f"Key not found: {key}")
        
        try:
            # Try to read as text first
            with open(file_path, 'r') as f:
                content = f.read()
            
            self.last_activity = datetime.now()
            return content
            
        except UnicodeDecodeError:
            # Read as binary
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.last_activity = datetime.now()
            return content
        
        except Exception as e:
            raise StorageError(f"Failed to retrieve {key}: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete data from filesystem.
        
        Args:
            key: File path relative to base_path
            
        Returns:
            True if deleted, False if not found
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)
        
        deleted = False
        
        try:
            # Delete main file
            if file_path.exists():
                file_path.unlink()
                deleted = True
            
            # Delete metadata file
            if metadata_path.exists():
                metadata_path.unlink()
            
            self.last_activity = datetime.now()
            return deleted
            
        except Exception as e:
            raise StorageError(f"Failed to delete {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in filesystem.
        
        Args:
            key: File path relative to base_path
            
        Returns:
            True if key exists
        """
        if not self.is_connected:
            return False
        
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    async def list_keys(self, prefix: str = "", limit: int = 1000) -> List[str]:
        """
        List keys with optional prefix filter.
        
        Args:
            prefix: Key prefix filter
            limit: Maximum number of keys to return
            
        Returns:
            List of keys
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        keys = []
        search_path = self.base_path
        
        if prefix:
            # Navigate to prefix directory if it exists
            prefix_path = self.base_path / prefix
            if prefix_path.exists() and prefix_path.is_dir():
                search_path = prefix_path
        
        try:
            for file_path in search_path.rglob("*"):
                if file_path.is_file() and not file_path.name.endswith(self.metadata_ext):
                    # Convert to relative key
                    relative_path = file_path.relative_to(self.base_path)
                    key = str(relative_path).replace(os.sep, "/")
                    
                    if not prefix or key.startswith(prefix):
                        keys.append(key)
                        
                        if len(keys) >= limit:
                            break
            
            self.last_activity = datetime.now()
            return sorted(keys)
            
        except Exception as e:
            raise StorageError(f"Failed to list keys: {e}")
    
    async def get_metadata(self, key: str) -> Optional[StorageMetadata]:
        """
        Get metadata for a key.
        
        Args:
            key: Storage key
            
        Returns:
            StorageMetadata or None if not found
        """
        if not self.is_connected:
            return None
        
        metadata_path = self._get_metadata_path(key)
        
        if not metadata_path.exists():
            # Create basic metadata from file stats
            file_path = self._get_file_path(key)
            if file_path.exists():
                stat = file_path.stat()
                return StorageMetadata(
                    key=key,
                    content_type="application/octet-stream",
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime)
                )
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)
            
            return StorageMetadata(
                key=metadata_dict["key"],
                content_type=metadata_dict.get("content_type", "application/octet-stream"),
                size=metadata_dict.get("size", 0),
                created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                modified_at=datetime.fromisoformat(metadata_dict["modified_at"]),
                version=metadata_dict.get("version", 1),
                tags=metadata_dict.get("tags", {})
            )
            
        except Exception as e:
            # Fallback to file stats
            file_path = self._get_file_path(key)
            if file_path.exists():
                stat = file_path.stat()
                return StorageMetadata(
                    key=key,
                    content_type="application/octet-stream",
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime)
                )
            return None
    
    def _get_file_path(self, key: str) -> Path:
        """Get filesystem path for a key."""
        # Sanitize key to prevent directory traversal
        safe_key = key.replace("..", "").strip("/")
        return self.base_path / safe_key
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for a key."""
        file_path = self._get_file_path(key)
        return file_path.with_suffix(file_path.suffix + self.metadata_ext)
    
    async def _store_metadata(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> None:
        """Store metadata for a key."""
        metadata = metadata or {}
        
        # Calculate size
        if isinstance(data, str):
            size = len(data.encode('utf-8'))
        elif isinstance(data, bytes):
            size = len(data)
        else:
            size = len(json.dumps(data, default=self._json_serializer))
        
        # Determine content type
        content_type = metadata.get("content_type", "application/json")
        if isinstance(data, str):
            content_type = "text/plain"
        elif isinstance(data, bytes):
            content_type = "application/octet-stream"
        
        metadata_obj = {
            "key": key,
            "content_type": content_type,
            "size": size,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "version": 1,
            "tags": metadata.get("tags", {}),
            **{k: v for k, v in metadata.items() if k not in ["content_type", "tags"]}
        }
        
        metadata_path = self._get_metadata_path(key)
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata_obj, f, indent=2)
        except Exception as e:
            # Metadata storage failure shouldn't fail the main operation
            print(f"Warning: Failed to store metadata for {key}: {e}")
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        if not self.is_connected:
            return {"error": "Storage not connected"}
        
        total_size = 0
        file_count = 0
        
        try:
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "file_count": file_count,
                "base_path": str(self.base_path)
            }
            
        except Exception as e:
            return {"error": str(e)}