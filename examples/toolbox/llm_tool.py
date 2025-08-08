"""
LLM Tool

Performs text generation using Azure OpenAI services.
Uses workflown's central configuration for Azure OpenAI settings.
"""

import asyncio
import json
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability


class LLMTool(BaseTool):
    """
    LLM tool using Azure OpenAI services.
    
    Provides text generation capabilities using Azure OpenAI API.
    Supports various text generation tasks like completion, chat, and summarization.
    Uses central configuration for Azure OpenAI settings.
    """
    
    def __init__(self, tool_id: str = None, config: Dict[str, Any] = None):
        """
        Initialize the LLM tool.
        
        Args:
            tool_id: Unique tool identifier
            config: Configuration dictionary (optional overrides)
        """
        super().__init__(
            tool_id=tool_id or "llm_tool",
            name="LLMTool",
            description="Performs text generation using Azure OpenAI services",
            capabilities=[
                ToolCapability.TEXT_GENERATION,
                ToolCapability.TEXT_SUMMARIZATION,
                ToolCapability.CUSTOM
            ],
            config=config,
            max_concurrent_operations=3  # Limit concurrent LLM calls
        )
        
        # Get Azure OpenAI configuration from central config
        self.azure_config = self._get_azure_config()
        
        # Override with provided config
        if config:
            self.azure_config.update(config)
        
        # Validate required configuration
        self._validate_azure_config()
        
        # Initialize Azure OpenAI client
        self.client = None
        self._initialize()
    
    def _get_azure_config(self) -> Dict[str, Any]:
        """Get Azure OpenAI configuration from central config."""
        try:
            # Import central config
            import sys
            sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', '..')))
            from workflown.core.config.central_config import get_config
            
            central_config = get_config()
            return central_config.get_azure_openai_config()
            
        except ImportError as e:
            # Fallback to environment variables if central config is not available
            print(f"Warning: Could not import central config: {e}")
            return {
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                "model_name": os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4o-mini"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                "max_tokens": int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "2000")),
                "temperature": float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.7"))
            }
    
    def _validate_azure_config(self) -> None:
        """Validate Azure OpenAI configuration."""
        required_fields = ["api_key", "endpoint", "deployment_name"]
        missing_fields = [field for field in required_fields if not self.azure_config.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required Azure OpenAI configuration: {missing_fields}")
    
    def _initialize(self):
        """Initialize Azure OpenAI client."""
        try:
            import openai
            
            # Get Azure config
            self.azure_config = self._get_azure_config()
            
            if not self.azure_config.get("api_key"):
                raise ValueError("Azure OpenAI API key not provided. Set AZURE_OPENAI_API_KEY environment variable or configure in central config.")
            
            # Configure Azure OpenAI client
            self.client = openai.AzureOpenAI(
                api_key=self.azure_config.get("api_key"),
                azure_endpoint=self.azure_config.get("endpoint"),
                api_version=self.azure_config.get("api_version", "2024-02-15-preview")
            )
            
            print(f"[INFO] Azure OpenAI client initialized successfully | model={self.azure_config.get('model_name')} | endpoint={self.azure_config.get('endpoint')}")
            
        except ImportError:
            raise Exception("openai package not installed. Install with: pip install openai")
        except Exception as e:
            raise Exception(f"Failed to initialize Azure OpenAI client: {str(e)}")
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute LLM text generation.
        
        Args:
            parameters: Dictionary containing:
                - prompt: Text prompt for generation
                - messages: List of chat messages (alternative to prompt)
                - max_tokens: Maximum tokens to generate
                - temperature: Sampling temperature (0.0-2.0)
                - operation_type: Type of operation (completion, chat, summarize)
                - system_prompt: System message for chat operations
        
        Returns:
            ToolResult with generated text
        """
        start_time = time.time()
        
        try:
            # Validate parameters
            if not self._validate_parameters(parameters):
                return ToolResult(
                    tool_id=self.tool_id,
                    success=False,
                    result=None,
                    errors=["Invalid parameters provided"]
                )
            
            # Extract parameters
            prompt = parameters.get("prompt", "")
            messages = parameters.get("messages", [])
            max_tokens = parameters.get("max_tokens", self.azure_config.get("max_tokens", 2000))
            temperature = parameters.get("temperature", self.azure_config.get("temperature", 0.7))
            operation_type = parameters.get("operation_type", "completion")
            system_prompt = parameters.get("system_prompt", "")
            
            await self._log_info(
                f"Starting Azure OpenAI {operation_type} operation",
                prompt_length=len(prompt),
                max_tokens=max_tokens,
                temperature=temperature,
                model=self.azure_config.get("model_name"),
                deployment=self.azure_config.get("deployment_name")
            )
            
            # Note: persistence is handled by BaseTool.execute_with_tracking. Do not persist here.

            # Generate response based on operation type
            if operation_type == "completion":
                result_text = await self._perform_text_completion(parameters)
            elif operation_type == "chat":
                result_text = await self._perform_chat_completion(parameters)
            elif operation_type == "summarize":
                result_text = await self._perform_summarization(parameters)
            else:
                result_text = await self._perform_text_completion(parameters)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            await self._log_info(
                f"Azure OpenAI {operation_type} completed successfully",
                execution_time=execution_time,
                result_length=len(result_text),
                model=self.azure_config.get("model_name")
            )
            
            tool_result = ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=result_text,
                metadata={
                    "operation_type": operation_type,
                    "execution_time": execution_time,
                    "model": self.azure_config.get("model_name"),
                    "deployment": self.azure_config.get("deployment_name"),
                    "provider": "azure_openai",
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )

            # Note: persistence is handled by BaseTool.execute_with_tracking. Do not persist here.

            return tool_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            await self._log_error(f"Azure OpenAI operation failed: {str(e)}")
            
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=[str(e)],
                metadata={"execution_time": execution_time}
            )
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        if not parameters:
            return False
        
        # Check for either prompt or messages
        if not parameters.get("prompt") and not parameters.get("messages"):
            return False
        
        # Validate token limits
        max_tokens = parameters.get("max_tokens", self.azure_config.get("max_tokens", 2000))
        if max_tokens <= 0 or max_tokens > 4000:
            return False
        
        # Validate temperature
        temperature = parameters.get("temperature", self.azure_config.get("temperature", 0.7))
        if temperature < 0.0 or temperature > 2.0:
            return False
        
        return True
    
    async def _perform_text_completion(self, parameters: Dict[str, Any]) -> str:
        """Perform text completion operation using Azure OpenAI."""
        prompt = parameters.get("prompt", "")
        max_tokens = parameters.get("max_tokens", self.azure_config.get("max_tokens", 2000))
        temperature = parameters.get("temperature", self.azure_config.get("temperature", 0.7))
        
        try:
            response = self.client.chat.completions.create(
                model=self.azure_config.get("deployment_name"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Azure OpenAI text completion failed: {str(e)}")
    
    async def _perform_chat_completion(self, parameters: Dict[str, Any]) -> str:
        """Perform chat completion operation using Azure OpenAI."""
        messages = parameters.get("messages", [])
        system_prompt = parameters.get("system_prompt", "")
        max_tokens = parameters.get("max_tokens", self.azure_config.get("max_tokens", 2000))
        temperature = parameters.get("temperature", self.azure_config.get("temperature", 0.7))
        
        try:
            chat_messages = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            
            # Add user messages
            if isinstance(messages, list):
                chat_messages.extend(messages)
            else:
                # If messages is a string, treat as user message
                chat_messages.append({"role": "user", "content": messages})
            
            response = self.client.chat.completions.create(
                model=self.azure_config.get("deployment_name"),
                messages=chat_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Azure OpenAI chat completion failed: {str(e)}")
    
    async def _perform_summarization(self, parameters: Dict[str, Any]) -> str:
        """Perform text summarization operation."""
        prompt = parameters.get("prompt", "")
        
        # Create summarization prompt
        summary_prompt = f"""
Please provide a comprehensive summary of the following content:

{prompt}

Summary:
"""
        
        # Use text completion with summarization prompt
        parameters["prompt"] = summary_prompt
        return await self._perform_text_completion(parameters)
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operation types."""
        return ["completion", "chat", "summarize", "generate_text"]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": self.azure_config.get("model_name"),
            "deployment_name": self.azure_config.get("deployment_name"),
            "endpoint": self.azure_config.get("endpoint"),
            "api_version": self.azure_config.get("api_version"),
            "provider": "azure_openai",
            "max_tokens": self.azure_config.get("max_tokens"),
            "temperature": self.azure_config.get("temperature"),
            "status": "active"
        }
    
    async def cleanup(self):
        """Clean up resources."""
        self.client = None
        await self._log_info("Azure OpenAI LLM tool cleanup completed")
    
    async def _log_info(self, message: str, **kwargs):
        """Log info message."""
        if hasattr(self, 'logger'):
            await self.logger.info(message, tool_id=self.tool_id, **kwargs)
        else:
            print(f"[INFO] {message} | {kwargs}")
    
    async def _log_error(self, message: str, **kwargs):
        """Log error message."""
        if hasattr(self, 'logger'):
            await self.logger.error(message, tool_id=self.tool_id, **kwargs)
        else:
            print(f"[ERROR] {message} | {kwargs}") 