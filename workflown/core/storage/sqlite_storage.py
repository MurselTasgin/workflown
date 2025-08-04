"""
SQLite Storage Implementation

SQLite-based storage backend for structured data and better querying.
"""

import sqlite3
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading

from .base_storage import BaseStorage, StorageBackend, StorageError, StorageMetadata


class SQLiteStorage(BaseStorage):
    """
    SQLite-based storage implementation.
    
    Provides structured storage with SQL querying capabilities.
    Suitable for single-node deployments with better query performance.
    """
    
    def __init__(self, storage_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize SQLite storage.
        
        Args:
            storage_id: Unique identifier
            config: Configuration including 'db_path'
        """
        super().__init__(storage_id, config)
        self.backend_type = StorageBackend.SQLITE
        
        # Database configuration
        self.db_path = config.get("db_path", "workflown.db") if config else "workflown.db"
        self.timeout = config.get("timeout", 30.0) if config else 30.0
        
        # Connection management
        self._local = threading.local()
        self._lock = threading.Lock()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.commit()
        
        return self._local.connection
    
    async def connect(self) -> None:
        """Connect to SQLite database and create tables."""
        try:
            # Create database file and directory if needed
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get connection and create tables
            conn = self._get_connection()
            
            # Create main storage table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS storage_data (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    content_type TEXT DEFAULT 'application/json',
                    size INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    tags TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            # Create index for better query performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON storage_data(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON storage_data(content_type)')
            
            # Create workflows table for better structure
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    state TEXT DEFAULT 'pending',
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create tasks table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT,
                    name TEXT,
                    task_type TEXT,
                    state TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 2,
                    data TEXT NOT NULL,
                    result TEXT,
                    assigned_executor TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
                )
            ''')
            
            # Create task results table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_results (
                    task_id TEXT PRIMARY KEY,
                    success BOOLEAN NOT NULL,
                    result TEXT,
                    error TEXT,
                    execution_time REAL DEFAULT 0.0,
                    executor_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_workflow ON tasks(workflow_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)')
            
            conn.commit()
            
            self.is_connected = True
            self.last_activity = datetime.now()
            
        except Exception as e:
            raise StorageError(f"Failed to connect to SQLite: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from SQLite database."""
        try:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
                delattr(self._local, 'connection')
            
            self.is_connected = False
            
        except Exception as e:
            print(f"Warning: Error during SQLite disconnect: {e}")
    
    async def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> str:
        """
        Store data in SQLite.
        
        Args:
            key: Storage key
            data: Data to store
            metadata: Optional metadata
            
        Returns:
            Storage key
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            
            # Serialize data
            if isinstance(data, (str, bytes)):
                data_str = data if isinstance(data, str) else data.decode('utf-8')
                content_type = "text/plain"
            else:
                data_str = json.dumps(data, default=self._json_serializer)
                content_type = "application/json"
            
            # Prepare metadata
            metadata = metadata or {}
            content_type = metadata.get("content_type", content_type)
            tags = json.dumps(metadata.get("tags", {}))
            metadata_json = json.dumps({k: v for k, v in metadata.items() if k not in ["content_type", "tags"]})
            size = len(data_str.encode('utf-8'))
            
            # Insert or update
            conn.execute('''
                INSERT OR REPLACE INTO storage_data 
                (key, data, content_type, size, modified_at, tags, metadata)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            ''', (key, data_str, content_type, size, tags, metadata_json))
            
            conn.commit()
            self.last_activity = datetime.now()
            
            return key
            
        except Exception as e:
            raise StorageError(f"Failed to store {key}: {e}")
    
    async def retrieve(self, key: str) -> Any:
        """
        Retrieve data from SQLite.
        
        Args:
            key: Storage key
            
        Returns:
            Retrieved data
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            cursor = conn.execute('SELECT data FROM storage_data WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row is None:
                raise StorageError(f"Key not found: {key}")
            
            self.last_activity = datetime.now()
            return row['data']
            
        except sqlite3.Error as e:
            if "Key not found" in str(e):
                raise
            raise StorageError(f"Failed to retrieve {key}: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete data from SQLite.
        
        Args:
            key: Storage key
            
        Returns:
            True if deleted, False if not found
        """
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            cursor = conn.execute('DELETE FROM storage_data WHERE key = ?', (key,))
            conn.commit()
            
            self.last_activity = datetime.now()
            return cursor.rowcount > 0
            
        except Exception as e:
            raise StorageError(f"Failed to delete {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in SQLite.
        
        Args:
            key: Storage key
            
        Returns:
            True if key exists
        """
        if not self.is_connected:
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.execute('SELECT 1 FROM storage_data WHERE key = ?', (key,))
            return cursor.fetchone() is not None
            
        except Exception:
            return False
    
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
        
        try:
            conn = self._get_connection()
            
            if prefix:
                cursor = conn.execute(
                    'SELECT key FROM storage_data WHERE key LIKE ? ORDER BY key LIMIT ?',
                    (f"{prefix}%", limit)
                )
            else:
                cursor = conn.execute(
                    'SELECT key FROM storage_data ORDER BY key LIMIT ?',
                    (limit,)
                )
            
            keys = [row['key'] for row in cursor.fetchall()]
            self.last_activity = datetime.now()
            
            return keys
            
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
        
        try:
            conn = self._get_connection()
            cursor = conn.execute('''
                SELECT content_type, size, created_at, modified_at, version, tags
                FROM storage_data WHERE key = ?
            ''', (key,))
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            return StorageMetadata(
                key=key,
                content_type=row['content_type'],
                size=row['size'],
                created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                modified_at=datetime.fromisoformat(row['modified_at'].replace('Z', '+00:00')),
                version=row['version'],
                tags=json.loads(row['tags']) if row['tags'] else {}
            )
            
        except Exception:
            return None
    
    # Specialized methods for structured data
    
    async def store_workflow_structured(self, workflow_id: str, workflow_data: Dict[str, Any]) -> str:
        """Store workflow in structured table."""
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            
            conn.execute('''
                INSERT OR REPLACE INTO workflows 
                (id, name, description, state, data, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                workflow_id,
                workflow_data.get('name', ''),
                workflow_data.get('description', ''),
                workflow_data.get('state', 'pending'),
                json.dumps(workflow_data, default=self._json_serializer)
            ))
            
            conn.commit()
            self.last_activity = datetime.now()
            
            return workflow_id
            
        except Exception as e:
            raise StorageError(f"Failed to store workflow {workflow_id}: {e}")
    
    async def store_task_structured(self, task_id: str, task_data: Dict[str, Any]) -> str:
        """Store task in structured table."""
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            
            conn.execute('''
                INSERT OR REPLACE INTO tasks 
                (id, workflow_id, name, task_type, state, priority, data, 
                 assigned_executor, updated_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            ''', (
                task_id,
                task_data.get('workflow_id'),
                task_data.get('name', ''),
                task_data.get('task_type', 'generic'),
                task_data.get('state', 'pending'),
                task_data.get('priority', 2),
                json.dumps(task_data, default=self._json_serializer),
                task_data.get('assigned_executor'),
                task_data.get('started_at'),
                task_data.get('completed_at')
            ))
            
            conn.commit()
            self.last_activity = datetime.now()
            
            return task_id
            
        except Exception as e:
            raise StorageError(f"Failed to store task {task_id}: {e}")
    
    async def get_workflows_by_state(self, state: str) -> List[Dict[str, Any]]:
        """Get workflows by state."""
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                'SELECT * FROM workflows WHERE state = ? ORDER BY created_at DESC',
                (state,)
            )
            
            workflows = []
            for row in cursor.fetchall():
                workflow = json.loads(row['data'])
                workflow.update({
                    'id': row['id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
                workflows.append(workflow)
            
            return workflows
            
        except Exception as e:
            raise StorageError(f"Failed to get workflows by state: {e}")
    
    async def get_tasks_by_workflow(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get tasks for a workflow."""
        if not self.is_connected:
            raise StorageError("Storage not connected")
        
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                'SELECT * FROM tasks WHERE workflow_id = ? ORDER BY created_at',
                (workflow_id,)
            )
            
            tasks = []
            for row in cursor.fetchall():
                task = json.loads(row['data'])
                task.update({
                    'id': row['id'],
                    'state': row['state'],
                    'assigned_executor': row['assigned_executor'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'started_at': row['started_at'],
                    'completed_at': row['completed_at']
                })
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            raise StorageError(f"Failed to get tasks for workflow: {e}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if not self.is_connected:
            return {"error": "Storage not connected"}
        
        try:
            conn = self._get_connection()
            
            # Get counts
            cursor = conn.execute('SELECT COUNT(*) as count FROM storage_data')
            total_items = cursor.fetchone()['count']
            
            cursor = conn.execute('SELECT COUNT(*) as count FROM workflows')
            workflow_count = cursor.fetchone()['count']
            
            cursor = conn.execute('SELECT COUNT(*) as count FROM tasks')
            task_count = cursor.fetchone()['count']
            
            # Get database size
            cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()['size']
            
            return {
                "total_items": total_items,
                "workflow_count": workflow_count,
                "task_count": task_count,
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / 1024 / 1024, 2),
                "database_path": self.db_path
            }
            
        except Exception as e:
            return {"error": str(e)}