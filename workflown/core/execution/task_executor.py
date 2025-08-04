"""
Task Executor Implementation

Generic task executor that can handle basic task types.
"""

import asyncio
import subprocess
import importlib
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import traceback

from .base_executor import BaseExecutor, ExecutorCapability, ExecutorStatus
from ..workflows.task import Task, TaskResult, TaskState


class TaskExecutor(BaseExecutor):
    """
    Generic task executor that can handle multiple task types.
    
    Supports:
    - Python code execution
    - Shell command execution
    - Function calls
    - Custom task handlers
    """
    
    def __init__(
        self,
        executor_id: str = None,
        name: str = "GenericTaskExecutor",
        description: str = "Generic task executor supporting multiple task types",
        max_concurrent_tasks: int = 5,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the task executor.
        
        Args:
            executor_id: Unique identifier
            name: Executor name
            description: Executor description
            max_concurrent_tasks: Maximum concurrent tasks
            config: Configuration dictionary
        """
        capabilities = [
            ExecutorCapability.GENERIC,
            ExecutorCapability.PYTHON,
            ExecutorCapability.SHELL,
            ExecutorCapability.HTTP
        ]
        
        super().__init__(
            executor_id=executor_id,
            name=name,
            description=description,
            capabilities=capabilities,
            max_concurrent_tasks=max_concurrent_tasks,
            config=config
        )
        
        # Task type handlers
        self.task_handlers = {
            "python": self._execute_python_task,
            "shell": self._execute_shell_task,
            "function": self._execute_function_task,
            "http": self._execute_http_task,
            "generic": self._execute_generic_task
        }
        
        # Safety settings
        self.allow_shell = config.get("allow_shell", False) if config else False
        self.python_timeout = config.get("python_timeout", 30) if config else 30
        self.shell_timeout = config.get("shell_timeout", 60) if config else 60
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task and return the result.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult containing execution results
        """
        if not self.can_handle_task(task):
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={"error": f"Cannot handle task type: {task.task_type}"},
                execution_time=0.0,
                timestamp=datetime.now(),
                errors=[f"Unsupported task type: {task.task_type}"]
            )
        
        # Check if we're at capacity
        if len(self.current_tasks) >= self.max_concurrent_tasks:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={"error": "Executor at capacity"},
                execution_time=0.0,
                timestamp=datetime.now(),
                errors=["Executor at maximum capacity"]
            )
        
        start_time = datetime.now()
        self.current_tasks[task.task_id] = task
        self.status = ExecutorStatus.BUSY
        
        try:
            # Run before_execute hooks
            await self._run_hooks("before_execute", task)
            
            # Execute the task
            handler = self.task_handlers.get(task.task_type, self._execute_generic_task)
            result = await handler(task)
            
            # Run after_execute hooks
            await self._run_hooks("after_execute", task, result)
            
            if result.success:
                self.completed_tasks += 1
                await self._run_hooks("on_success", task, result)
            else:
                self.failed_tasks += 1
                await self._run_hooks("on_error", task, result)
            
            return result
        
        except Exception as e:
            error_msg = f"Executor error: {str(e)}"
            traceback_str = traceback.format_exc()
            
            self.failed_tasks += 1
            result = TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={
                    "error": error_msg,
                    "traceback": traceback_str,
                    "executor_id": self.executor_id
                },
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                errors=[error_msg]
            )
            
            await self._run_hooks("on_error", task, result)
            return result
        
        finally:
            # Clean up
            if task.task_id in self.current_tasks:
                del self.current_tasks[task.task_id]
            
            if len(self.current_tasks) == 0:
                self.status = ExecutorStatus.IDLE
            
            self.last_activity = datetime.now()
    
    def can_handle_task(self, task: Task) -> bool:
        """
        Check if this executor can handle the given task.
        
        Args:
            task: Task to check
            
        Returns:
            True if executor can handle the task
        """
        return task.task_type in self.task_handlers
    
    def get_supported_task_types(self) -> List[str]:
        """
        Get list of supported task types.
        
        Returns:
            List of supported task type strings
        """
        return list(self.task_handlers.keys())
    
    async def _execute_python_task(self, task: Task) -> TaskResult:
        """Execute a Python code task."""
        start_time = datetime.now()
        
        try:
            code = task.parameters.get("code", "")
            if not code:
                raise ValueError("No Python code provided")
            
            # Create execution namespace
            namespace = {
                "task": task,
                "parameters": task.parameters,
                "__name__": "__task__"
            }
            
            # Add any additional globals
            globals_dict = task.parameters.get("globals", {})
            namespace.update(globals_dict)
            
            # Execute with timeout
            try:
                exec(code, namespace)
                result = namespace.get("result", "Task completed successfully")
            except Exception as e:
                raise RuntimeError(f"Python execution error: {str(e)}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.task_id,
                success=True,
                result=result,
                metadata={
                    "task_type": "python",
                    "executor_id": self.executor_id,
                    "namespace_keys": list(namespace.keys())
                },
                execution_time=execution_time,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={
                    "task_type": "python",
                    "executor_id": self.executor_id,
                    "error": str(e)
                },
                execution_time=execution_time,
                timestamp=datetime.now(),
                errors=[str(e)]
            )
    
    async def _execute_shell_task(self, task: Task) -> TaskResult:
        """Execute a shell command task."""
        if not self.allow_shell:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={"error": "Shell execution not allowed"},
                execution_time=0.0,
                timestamp=datetime.now(),
                errors=["Shell execution disabled for security"]
            )
        
        start_time = datetime.now()
        
        try:
            command = task.parameters.get("command", "")
            if not command:
                raise ValueError("No shell command provided")
            
            cwd = task.parameters.get("cwd", None)
            env = task.parameters.get("env", None)
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.shell_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise RuntimeError(f"Shell command timed out after {self.shell_timeout}s")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.task_id,
                success=process.returncode == 0,
                result={
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "returncode": process.returncode
                },
                metadata={
                    "task_type": "shell",
                    "executor_id": self.executor_id,
                    "command": command
                },
                execution_time=execution_time,
                timestamp=datetime.now(),
                errors=[stderr.decode()] if stderr and process.returncode != 0 else []
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={
                    "task_type": "shell",
                    "executor_id": self.executor_id,
                    "error": str(e)
                },
                execution_time=execution_time,
                timestamp=datetime.now(),
                errors=[str(e)]
            )
    
    async def _execute_function_task(self, task: Task) -> TaskResult:
        """Execute a function call task."""
        start_time = datetime.now()
        
        try:
            function_path = task.parameters.get("function", "")
            args = task.parameters.get("args", [])
            kwargs = task.parameters.get("kwargs", {})
            
            if not function_path:
                raise ValueError("No function path provided")
            
            # Import and call function
            module_path, function_name = function_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            function = getattr(module, function_name)
            
            # Call function
            if asyncio.iscoroutinefunction(function):
                result = await function(*args, **kwargs)
            else:
                result = function(*args, **kwargs)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.task_id,
                success=True,
                result=result,
                metadata={
                    "task_type": "function",
                    "executor_id": self.executor_id,
                    "function": function_path
                },
                execution_time=execution_time,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={
                    "task_type": "function",
                    "executor_id": self.executor_id,
                    "error": str(e)
                },
                execution_time=execution_time,
                timestamp=datetime.now(),
                errors=[str(e)]
            )
    
    async def _execute_http_task(self, task: Task) -> TaskResult:
        """Execute an HTTP request task."""
        start_time = datetime.now()
        
        try:
            # This would need an HTTP client library like aiohttp
            # For now, return a placeholder
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={
                    "task_type": "http",
                    "executor_id": self.executor_id,
                    "error": "HTTP client not implemented"
                },
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                errors=["HTTP task execution not yet implemented"]
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                success=False,
                result=None,
                metadata={
                    "task_type": "http",
                    "executor_id": self.executor_id,
                    "error": str(e)
                },
                execution_time=execution_time,
                timestamp=datetime.now(),
                errors=[str(e)]
            )
    
    async def _execute_generic_task(self, task: Task) -> TaskResult:
        """Execute a generic task."""
        start_time = datetime.now()
        
        # Generic task just returns success with task parameters
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return TaskResult(
            task_id=task.task_id,
            success=True,
            result=f"Generic task '{task.name}' completed",
            metadata={
                "task_type": "generic",
                "executor_id": self.executor_id,
                "parameters": task.parameters
            },
            execution_time=execution_time,
            timestamp=datetime.now()
        )