"""
Log Handlers

Various handlers for outputting logs to different destinations.
"""

import asyncio
import sys
from typing import Dict, List, Any, Optional, TextIO
from pathlib import Path
from datetime import datetime
import json

from .logger import LogHandler, LogEntry, LogLevel


class ConsoleHandler(LogHandler):
    """Handler that outputs logs to console/terminal."""
    
    def __init__(
        self,
        name: str = "console",
        level: LogLevel = LogLevel.INFO,
        stream: TextIO = None,
        colored: bool = True
    ):
        """
        Initialize console handler.
        
        Args:
            name: Handler name
            level: Minimum log level
            stream: Output stream (defaults to stderr)
            colored: Whether to use colored output
        """
        super().__init__(name, level)
        self.stream = stream or sys.stderr
        self.colored = colored
        
        # Color codes for different log levels
        self.colors = {
            LogLevel.DEBUG: "\033[36m",    # Cyan
            LogLevel.INFO: "\033[32m",     # Green
            LogLevel.WARNING: "\033[33m",  # Yellow
            LogLevel.ERROR: "\033[31m",    # Red
            LogLevel.CRITICAL: "\033[35m", # Magenta
        }
        self.reset_color = "\033[0m"
    
    async def emit(self, entry: LogEntry) -> None:
        """Emit log entry to console."""
        try:
            formatted = self.format(entry)
            
            if self.colored and entry.level in self.colors:
                formatted = f"{self.colors[entry.level]}{formatted}{self.reset_color}"
            
            print(formatted, file=self.stream)
            self.stream.flush()
            
        except Exception as e:
            # Fallback to basic print to avoid infinite recursion
            print(f"ConsoleHandler error: {e}", file=sys.stderr)


class FileHandler(LogHandler):
    """Handler that outputs logs to a file."""
    
    def __init__(
        self,
        name: str = "file",
        level: LogLevel = LogLevel.INFO,
        filename: str = "workflown.log",
        max_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        encoding: str = "utf-8"
    ):
        """
        Initialize file handler.
        
        Args:
            name: Handler name
            level: Minimum log level
            filename: Log file path
            max_size: Maximum file size before rotation
            backup_count: Number of backup files to keep
            encoding: File encoding
        """
        super().__init__(name, level)
        self.filename = Path(filename)
        self.max_size = max_size
        self.backup_count = backup_count
        self.encoding = encoding
        
        # Create directory if needed
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        
        # File handle
        self._file = None
        self._lock = asyncio.Lock()
    
    async def emit(self, entry: LogEntry) -> None:
        """Emit log entry to file."""
        async with self._lock:
            try:
                # Open file if needed
                if self._file is None or self._file.closed:
                    self._file = open(self.filename, 'a', encoding=self.encoding)
                
                # Check if rotation is needed
                if self._file.tell() > self.max_size:
                    await self._rotate_file()
                
                # Write log entry
                formatted = self.format(entry)
                self._file.write(formatted + '\n')
                self._file.flush()
                
            except Exception as e:
                print(f"FileHandler error: {e}", file=sys.stderr)
    
    async def _rotate_file(self) -> None:
        """Rotate log file when it gets too large."""
        try:
            if self._file:
                self._file.close()
            
            # Rotate existing backup files
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = self.filename.with_suffix(f"{self.filename.suffix}.{i}")
                new_backup = self.filename.with_suffix(f"{self.filename.suffix}.{i + 1}")
                
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)
            
            # Move current file to .1
            if self.filename.exists():
                backup = self.filename.with_suffix(f"{self.filename.suffix}.1")
                if backup.exists():
                    backup.unlink()
                self.filename.rename(backup)
            
            # Open new file
            self._file = open(self.filename, 'w', encoding=self.encoding)
            
        except Exception as e:
            print(f"FileHandler rotation error: {e}", file=sys.stderr)
    
    async def close(self) -> None:
        """Close the file handler."""
        async with self._lock:
            if self._file and not self._file.closed:
                self._file.close()


class StructuredHandler(LogHandler):
    """Handler that outputs structured logs (JSON) to a file."""
    
    def __init__(
        self,
        name: str = "structured",
        level: LogLevel = LogLevel.INFO,
        filename: str = "workflown-structured.log",
        max_size: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 10,
        encoding: str = "utf-8"
    ):
        """
        Initialize structured handler.
        
        Args:
            name: Handler name
            level: Minimum log level
            filename: Log file path
            max_size: Maximum file size before rotation
            backup_count: Number of backup files to keep
            encoding: File encoding
        """
        super().__init__(name, level)
        self.filename = Path(filename)
        self.max_size = max_size
        self.backup_count = backup_count
        self.encoding = encoding
        
        # Create directory if needed
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        
        # File handle
        self._file = None
        self._lock = asyncio.Lock()
    
    async def emit(self, entry: LogEntry) -> None:
        """Emit log entry as JSON to file."""
        async with self._lock:
            try:
                # Open file if needed
                if self._file is None or self._file.closed:
                    self._file = open(self.filename, 'a', encoding=self.encoding)
                
                # Check if rotation is needed
                if self._file.tell() > self.max_size:
                    await self._rotate_file()
                
                # Write JSON log entry
                json_data = entry.to_dict()
                json_line = json.dumps(json_data, default=str, separators=(',', ':'))
                self._file.write(json_line + '\n')
                self._file.flush()
                
            except Exception as e:
                print(f"StructuredHandler error: {e}", file=sys.stderr)
    
    async def _rotate_file(self) -> None:
        """Rotate log file when it gets too large."""
        try:
            if self._file:
                self._file.close()
            
            # Rotate existing backup files
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = self.filename.with_suffix(f"{self.filename.suffix}.{i}")
                new_backup = self.filename.with_suffix(f"{self.filename.suffix}.{i + 1}")
                
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)
            
            # Move current file to .1
            if self.filename.exists():
                backup = self.filename.with_suffix(f"{self.filename.suffix}.1")
                if backup.exists():
                    backup.unlink()
                self.filename.rename(backup)
            
            # Open new file
            self._file = open(self.filename, 'w', encoding=self.encoding)
            
        except Exception as e:
            print(f"StructuredHandler rotation error: {e}", file=sys.stderr)
    
    async def close(self) -> None:
        """Close the structured handler."""
        async with self._lock:
            if self._file and not self._file.closed:
                self._file.close()


class BufferedHandler(LogHandler):
    """Handler that buffers log entries in memory."""
    
    def __init__(
        self,
        name: str = "buffer",
        level: LogLevel = LogLevel.INFO,
        max_entries: int = 1000,
        flush_interval: float = 5.0
    ):
        """
        Initialize buffered handler.
        
        Args:
            name: Handler name
            level: Minimum log level
            max_entries: Maximum entries to buffer
            flush_interval: Interval to flush buffer (seconds)
        """
        super().__init__(name, level)
        self.max_entries = max_entries
        self.flush_interval = flush_interval
        
        self.buffer: List[LogEntry] = []
        self._lock = asyncio.Lock()
        self._flush_task = None
        self._running = False
    
    async def start(self) -> None:
        """Start the buffered handler."""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_periodically())
    
    async def stop(self) -> None:
        """Stop the buffered handler."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining entries
        await self.flush()
    
    async def emit(self, entry: LogEntry) -> None:
        """Add log entry to buffer."""
        async with self._lock:
            self.buffer.append(entry)
            
            # Flush if buffer is full
            if len(self.buffer) >= self.max_entries:
                await self._flush_buffer()
    
    async def flush(self) -> List[LogEntry]:
        """Flush buffer and return entries."""
        async with self._lock:
            entries = self.buffer.copy()
            self.buffer.clear()
            return entries
    
    async def get_entries(self, limit: int = None) -> List[LogEntry]:
        """Get buffered entries without flushing."""
        async with self._lock:
            if limit:
                return self.buffer[-limit:]
            return self.buffer.copy()
    
    async def _flush_buffer(self) -> None:
        """Internal flush method."""
        if self.buffer:
            # Override in subclasses to do something with flushed entries
            pass
    
    async def _flush_periodically(self) -> None:
        """Periodically flush the buffer."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                if self.buffer:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"BufferedHandler flush error: {e}", file=sys.stderr)


class WebhookHandler(LogHandler):
    """Handler that sends logs to a webhook endpoint."""
    
    def __init__(
        self,
        name: str = "webhook",
        level: LogLevel = LogLevel.ERROR,
        webhook_url: str = "",
        timeout: float = 10.0,
        retry_count: int = 3,
        batch_size: int = 10
    ):
        """
        Initialize webhook handler.
        
        Args:
            name: Handler name
            level: Minimum log level
            webhook_url: Webhook URL to send logs to
            timeout: Request timeout
            retry_count: Number of retries on failure
            batch_size: Number of logs to batch together
        """
        super().__init__(name, level)
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.retry_count = retry_count
        self.batch_size = batch_size
        
        self.pending_entries: List[LogEntry] = []
        self._lock = asyncio.Lock()
    
    async def emit(self, entry: LogEntry) -> None:
        """Add log entry to pending batch."""
        async with self._lock:
            self.pending_entries.append(entry)
            
            if len(self.pending_entries) >= self.batch_size:
                await self._send_batch()
    
    async def flush(self) -> None:
        """Send any pending entries."""
        async with self._lock:
            if self.pending_entries:
                await self._send_batch()
    
    async def _send_batch(self) -> None:
        """Send batch of log entries to webhook."""
        if not self.webhook_url or not self.pending_entries:
            return
        
        entries = self.pending_entries.copy()
        self.pending_entries.clear()
        
        payload = {
            "logs": [entry.to_dict() for entry in entries],
            "timestamp": datetime.now().isoformat(),
            "source": "workflown"
        }
        
        # Note: This would need an HTTP client like aiohttp
        # For now, just print the payload
        print(f"WebhookHandler would send to {self.webhook_url}: {len(entries)} entries")
        
        # In a real implementation:
        # try:
        #     async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
        #         async with session.post(self.webhook_url, json=payload) as response:
        #             if response.status != 200:
        #                 print(f"Webhook error: {response.status}")
        # except Exception as e:
        #     print(f"Webhook send error: {e}")


class MemoryHandler(BufferedHandler):
    """Handler that keeps logs in memory for inspection."""
    
    def __init__(
        self,
        name: str = "memory",
        level: LogLevel = LogLevel.DEBUG,
        max_entries: int = 5000
    ):
        """
        Initialize memory handler.
        
        Args:
            name: Handler name
            level: Minimum log level
            max_entries: Maximum entries to keep in memory
        """
        super().__init__(name, level, max_entries, flush_interval=float('inf'))
        self.persistent_buffer: List[LogEntry] = []
    
    async def emit(self, entry: LogEntry) -> None:
        """Add log entry to persistent memory buffer."""
        async with self._lock:
            self.persistent_buffer.append(entry)
            
            # Keep only the most recent entries
            if len(self.persistent_buffer) > self.max_entries:
                self.persistent_buffer = self.persistent_buffer[-self.max_entries:]
    
    async def get_recent_logs(self, limit: int = 100, level: LogLevel = None) -> List[LogEntry]:
        """Get recent log entries."""
        async with self._lock:
            entries = self.persistent_buffer
            
            if level:
                entries = [e for e in entries if e.level >= level]
            
            return entries[-limit:] if limit else entries
    
    async def search_logs(
        self,
        query: str = "",
        level: LogLevel = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """Search log entries by various criteria."""
        async with self._lock:
            entries = self.persistent_buffer
            
            # Filter by level
            if level:
                entries = [e for e in entries if e.level >= level]
            
            # Filter by time range
            if start_time:
                entries = [e for e in entries if e.timestamp >= start_time]
            if end_time:
                entries = [e for e in entries if e.timestamp <= end_time]
            
            # Filter by query (search in message and context)
            if query:
                query_lower = query.lower()
                filtered = []
                for entry in entries:
                    if (query_lower in entry.message.lower() or
                        query_lower in str(entry.context).lower() or
                        query_lower in entry.logger_name.lower()):
                        filtered.append(entry)
                entries = filtered
            
            return entries[-limit:] if limit else entries