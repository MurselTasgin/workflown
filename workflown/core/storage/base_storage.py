"""
Base Storage Interface

Defines the interface for persistent storage backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json


class StorageBackend(Enum):
    """Types of storage backends."""
    FILESYSTEM = "filesystem"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    REDIS = "redis"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


@dataclass
class StorageMetadata:
    """Metadata for stored objects."""
    key: str
    content_type: str
    size: int
    created_at: datetime
    modified_at: datetime
    version: int = 1
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class BaseStorage(ABC):
    """
    Abstract base class for storage backends.
    
    Provides a common interface for storing and retrieving
    workflow data, task results, and system state.
    """
    
    def __init__(self, storage_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize the storage backend.
        
        Args:
            storage_id: Unique identifier for this storage instance
            config: Storage configuration
        """
        self.storage_id = storage_id or "default"
        self.config = config or {}
        self.backend_type = StorageBackend.FILESYSTEM  # Override in subclasses
        self.is_connected = False
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass
    
    @abstractmethod
    async def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> str:
        """
        Store data with the given key.
        
        Args:
            key: Storage key/path
            data: Data to store
            metadata: Optional metadata
            
        Returns:
            Storage key or identifier
        """
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Any:
        """
        Retrieve data by key.
        
        Args:
            key: Storage key/path
            
        Returns:
            Retrieved data
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete data by key.
        
        Args:
            key: Storage key/path
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Storage key/path
            
        Returns:
            True if key exists
        """
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: str = "", limit: int = 1000) -> List[str]:
        """
        List keys with optional prefix filter.
        
        Args:
            prefix: Key prefix filter
            limit: Maximum number of keys to return
            
        Returns:
            List of keys
        """
        pass
    
    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[StorageMetadata]:
        """
        Get metadata for a key.
        
        Args:
            key: Storage key/path
            
        Returns:
            StorageMetadata or None if not found
        """
        pass
    
    async def store_json(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> str:
        """
        Store data as JSON.
        
        Args:
            key: Storage key
            data: Data to serialize and store
            metadata: Optional metadata
            
        Returns:
            Storage key
        """
        json_data = json.dumps(data, default=self._json_serializer, indent=2)
        return await self.store(key, json_data, metadata)
    
    async def retrieve_json(self, key: str) -> Any:
        """
        Retrieve and deserialize JSON data.
        
        Args:
            key: Storage key
            
        Returns:
            Deserialized data
        """
        json_data = await self.retrieve(key)
        if isinstance(json_data, bytes):
            json_data = json_data.decode('utf-8')
        return json.loads(json_data)
    
    async def store_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> str:
        """
        Store workflow data.
        
        Args:
            workflow_id: Workflow identifier
            workflow_data: Workflow data
            
        Returns:
            Storage key
        """
        key = f"workflows/{workflow_id}"
        metadata = {
            "type": "workflow",
            "workflow_id": workflow_id,
            "stored_at": datetime.now().isoformat()
        }
        return await self.store_json(key, workflow_data, metadata)
    
    async def retrieve_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve workflow data.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow data or None if not found
        """
        key = f"workflows/{workflow_id}"
        try:
            return await self.retrieve_json(key)
        except StorageError:
            return None
    
    async def store_task(self, task_id: str, task_data: Dict[str, Any]) -> str:
        """
        Store task data.
        
        Args:
            task_id: Task identifier
            task_data: Task data
            
        Returns:
            Storage key
        """
        key = f"tasks/{task_id}"
        metadata = {
            "type": "task",
            "task_id": task_id,
            "stored_at": datetime.now().isoformat()
        }
        return await self.store_json(key, task_data, metadata)
    
    async def retrieve_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve task data.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task data or None if not found
        """
        key = f"tasks/{task_id}"
        try:
            return await self.retrieve_json(key)
        except StorageError:
            return None
    
    async def store_execution_result(self, task_id: str, result_data: Dict[str, Any]) -> str:
        """
        Store task execution result.
        
        Args:
            task_id: Task identifier
            result_data: Execution result data
            
        Returns:
            Storage key
        """
        key = f"results/{task_id}"
        metadata = {
            "type": "result",
            "task_id": task_id,
            "stored_at": datetime.now().isoformat()
        }
        return await self.store_json(key, result_data, metadata)
    
    async def retrieve_execution_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve task execution result.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Execution result or None if not found
        """
        key = f"results/{task_id}"
        try:
            return await self.retrieve_json(key)
        except StorageError:
            return None
    
    async def list_workflows(self, limit: int = 100) -> List[str]:
        """
        List workflow IDs.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of workflow IDs
        """
        keys = await self.list_keys("workflows/", limit)
        return [key.split("/", 1)[1] for key in keys]
    
    async def list_tasks(self, limit: int = 100) -> List[str]:
        """
        List task IDs.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of task IDs
        """
        keys = await self.list_keys("tasks/", limit)
        return [key.split("/", 1)[1] for key in keys]
    
    async def cleanup_old_data(self, older_than_days: int = 30) -> int:
        """
        Clean up old data.
        
        Args:
            older_than_days: Delete data older than this many days
            
        Returns:
            Number of items deleted
        """
        cutoff_date = datetime.now().timestamp() - (older_than_days * 24 * 3600)
        deleted_count = 0
        
        # Get all keys
        all_keys = await self.list_keys()
        
        for key in all_keys:
            metadata = await self.get_metadata(key)
            if metadata and metadata.created_at.timestamp() < cutoff_date:
                if await self.delete(key):
                    deleted_count += 1
        
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary containing storage stats
        """
        return {
            "storage_id": self.storage_id,
            "backend_type": self.backend_type.value,
            "is_connected": self.is_connected,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    def _json_serializer(self, obj: Any) -> str:
        """
        JSON serializer for complex objects.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized string
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on storage backend.
        
        Returns:
            Health check results
        """
        health = {
            "healthy": True,
            "backend": self.backend_type.value,
            "connected": self.is_connected,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Try a simple operation
            test_key = f"_health_check_{datetime.now().timestamp()}"
            await self.store(test_key, "health_check_data")
            exists = await self.exists(test_key)
            await self.delete(test_key)
            
            if not exists:
                health["healthy"] = False
                health["error"] = "Health check store/retrieve failed"
        
        except Exception as e:
            health["healthy"] = False
            health["error"] = str(e)
        
        return health