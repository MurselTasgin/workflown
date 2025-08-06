"""
LLM Composer Tool

Uses Large Language Models to compose, summarize, and analyze text content.
Integrates with Azure OpenAI for actual LLM processing.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from base_tool import BaseTool, ToolResult, ToolCapability
from llm_tool import LLMTool


class ComposerTool(BaseTool):
    """
    LLM Composer tool for text generation, summarization, and analysis.
    
    Integrates with Azure OpenAI LLM tool for actual text processing.
    """
    
    def __init__(self, tool_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            tool_id=tool_id or "composer_tool",
            name="ComposerTool",
            description="Uses LLMs for text composition, summarization, and analysis",
            capabilities=[ToolCapability.TEXT_GENERATION, ToolCapability.TEXT_SUMMARIZATION],
            config=config,
            max_concurrent_operations=3
        )
        
        # Configuration
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 2000)
        self.max_input_tokens = self.config.get("max_input_tokens", 8000)
        
        # Initialize LLM tool
        self.llm_tool = LLMTool(
            tool_id=f"{self.tool_id}_llm",
            config=self.config
        )
        
        # Set provider and model info for logging
        self.provider = self.config.get("provider", "azure_openai")
        # Get model info from LLM tool
        llm_info = self.llm_tool.get_model_info()
        self.model = llm_info.get("model_name", "gpt-4o-mini")
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute LLM composition task.
        
        Args:
            parameters: Composition parameters including:
                - task: Type of task ("summarize", "analyze", "compose", "combine")
                - content: Text content to process (str or list of str)
                - query: User query/instructions for the task
                - format: Output format ("text", "json", "markdown")
                - max_length: Maximum output length
                - include_sources: Include source references (for combine task)
        
        Returns:
            ToolResult with composed content
        """
        task = parameters.get("task", "summarize")
        content = parameters.get("content", "")
        query = parameters.get("query", "")
        output_format = parameters.get("format", "text")
        max_length = parameters.get("max_length", self.max_tokens)
        include_sources = parameters.get("include_sources", True)
        
        if not content:
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=["No content provided for composition"]
            )
        
        await self._log_info(
            f"Starting LLM composition task",
            task=task,
            content_length=len(str(content)),
            provider=self.provider,
            model=self.model
        )
        
        try:
            # Prepare content for processing
            processed_content = self._prepare_content(content, task)
            
            # Generate prompt based on task
            prompt = self._generate_prompt(task, processed_content, query, output_format, include_sources)
            
            # Check token limits
            if len(prompt) > self.max_input_tokens * 4:  # Rough estimate (4 chars per token)
                prompt = prompt[:self.max_input_tokens * 4]
                await self._log_warning("Content truncated due to token limits")
            
            # Call actual LLM using LLM tool
            response = await self._call_llm(prompt, max_length, task, query)
            
            # Post-process response
            final_result = self._post_process_response(response, output_format)
            
            return ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=final_result,
                metadata={
                    "task": task,
                    "provider": self.provider,
                    "model": self.model,
                    "input_length": len(processed_content),
                    "output_length": len(final_result),
                    "format": output_format
                }
            )
            
        except Exception as e:
            await self._log_error(f"LLM composition failed", task=task, error=str(e))
            
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                errors=[str(e)]
            )
    
    def _prepare_content(self, content: Union[str, List[str], List[Dict]], task: str) -> str:
        """Prepare content for LLM processing."""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            if not content:
                return ""
            
            # Handle list of strings
            if isinstance(content[0], str):
                return "\n\n---\n\n".join(content)
            
            # Handle list of dictionaries (e.g., web page results)
            elif isinstance(content[0], dict):
                formatted_content = []
                for i, item in enumerate(content, 1):
                    title = item.get('title', f'Source {i}')
                    url = item.get('url', '')
                    text_content = item.get('content', '') or item.get('summary', '')
                    
                    source_text = f"## Source {i}: {title}\n"
                    if url:
                        source_text += f"URL: {url}\n"
                    source_text += f"\n{text_content}\n"
                    
                    formatted_content.append(source_text)
                
                return "\n\n---\n\n".join(formatted_content)
        
        return str(content)
    
    def _generate_prompt(
        self,
        task: str,
        content: str,
        query: str,
        output_format: str,
        include_sources: bool
    ) -> str:
        """Generate appropriate prompt based on task type."""
        base_prompts = {
            "summarize": "Please provide a comprehensive summary of the following content:",
            "analyze": "Please analyze the following content and provide key insights:",
            "compose": "Please compose a well-structured response based on the following content:",
            "combine": "Please combine and synthesize the following sources into a coherent analysis:"
        }
        
        prompt = base_prompts.get(task, base_prompts["summarize"])
        
        if query:
            prompt += f"\n\nSpecific focus: {query}"
        
        # Add format instructions
        if output_format == "json":
            prompt += "\n\nPlease format your response as valid JSON with appropriate fields."
        elif output_format == "markdown":
            prompt += "\n\nPlease format your response in Markdown with proper headings and structure."
        
        if include_sources and task == "combine":
            prompt += "\n\nPlease include references to the sources in your response."
        
        prompt += f"\n\nContent to process:\n\n{content}"
        
        return prompt
    
    async def _call_llm(self, prompt: str, max_tokens: int, task: str, query: str) -> str:
        """Call actual LLM using LLM tool."""
        try:
            # Determine operation type based on task
            operation_type = "completion"
            if task == "summarize":
                operation_type = "summarize"
            
            # Call LLM tool
            result = await self.llm_tool.execute({
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": self.temperature,
                "operation_type": operation_type
            })
            
            if result.success:
                return result.result
            else:
                raise Exception(f"LLM call failed: {result.errors}")
                
        except Exception as e:
            await self._log_error(f"LLM call failed: {str(e)}")
            raise Exception(f"Failed to call LLM: {str(e)}")
    
    def _post_process_response(self, response: str, output_format: str) -> str:
        """Post-process LLM response based on format requirements."""
        if output_format == "json":
            try:
                # Wrap response in JSON format
                return json.dumps({
                    "content": response,
                    "format": "markdown",
                    "generated_at": datetime.now().isoformat(),
                    "word_count": len(response.split())
                }, indent=2)
            except:
                return json.dumps({"content": response}, indent=2)
        
        return response
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of available LLM providers."""
        llm_info = self.llm_tool.get_model_info()
        return {
            "current_provider": "azure_openai",
            "current_model": llm_info.get("model_name", "gpt-4o-mini"),
            "deployment_name": llm_info.get("deployment_name"),
            "endpoint": llm_info.get("endpoint"),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "llm_tool_status": "active"
        }
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operation types."""
        return ["summarize", "analyze", "compose", "combine", "generate_text"]
    
    async def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'llm_tool'):
            await self.llm_tool.cleanup()
    
    # Logging helpers
    async def _log_info(self, message: str, **kwargs):
        """Log info message."""
        if hasattr(self, 'logger'):
            await self.logger.info(message, tool_id=self.tool_id, **kwargs)
        else:
            print(f"[INFO] {message} | {kwargs}")
    
    async def _log_warning(self, message: str, **kwargs):
        """Log warning message."""
        if hasattr(self, 'logger'):
            await self.logger.warning(message, tool_id=self.tool_id, **kwargs)
        else:
            print(f"[WARNING] {message} | {kwargs}")
    
    async def _log_error(self, message: str, **kwargs):
        """Log error message."""
        if hasattr(self, 'logger'):
            await self.logger.error(message, tool_id=self.tool_id, **kwargs)
        else:
            print(f"[ERROR] {message} | {kwargs}")