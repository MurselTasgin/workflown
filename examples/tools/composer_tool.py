"""
Composer Tool

Uses Azure OpenAI for text generation, summarization, and composition.
"""

import asyncio
import json
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime
from openai import AzureOpenAI

from .base_tool import BaseTool, ToolResult, ToolCapability
from workflown.core.config.central_config import get_config


class ComposerTool(BaseTool):
    """
    Tool for text generation and composition using LLM.
    
    Supports various text generation tasks including:
    - Summarization
    - Report generation
    - Content composition
    - Text analysis
    """
    
    def __init__(
        self,
        tool_id: str = None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the composer tool.
        
        Args:
            tool_id: Unique tool identifier
            config: Configuration dictionary
        """
        super().__init__(
            tool_id=tool_id,
            name="ComposerTool",
            description="Generates and composes text using LLM",
            capabilities=[
                ToolCapability.TEXT_GENERATION,
                ToolCapability.TEXT_SUMMARIZATION,
                ToolCapability.DATA_PROCESSING
            ],
            config=config,
            max_concurrent_operations=5
        )
        
        # Session for HTTP requests
        self.session = None
        
        # LLM configuration (will be set in _initialize)
        self.llm_config = None
        self.api_key = None
        self.model = None
        self.max_tokens = None
        self.temperature = None
        self.api_base = None
        self.api_endpoint = None
        
        # Prompt templates (will be set in _initialize)
        self.prompt_templates = None
        # Call initialize after all attributes are set
        self._initialize()
    
    def _initialize(self):
        """Initialize Azure OpenAI components."""
        print(f"DEBUG: ComposerTool._initialize() called for tool_id: {self.tool_id}")
        
        # Get Azure OpenAI configuration from central config
        central_config = get_config()
        azure_config = central_config.get_azure_openai_config()
        
        # Override with local config if provided
        if self.config.get("azure_openai"):
            azure_config.update(self.config["azure_openai"])
        
        # Azure OpenAI configuration
        self.api_key = azure_config.get("api_key")
        self.endpoint = azure_config.get("endpoint")
        self.deployment_name = azure_config.get("deployment_name", "gpt-4o-mini")
        self.api_version = azure_config.get("api_version", "2024-02-15-preview")
        self.max_tokens = azure_config.get("max_tokens", 2000)
        self.temperature = azure_config.get("temperature", 0.7)

        print("--------------------------------")       
        print(f"Azure OpenAI configuration: API key: {self.api_key}")
        print(f"Azure Endpoint: {self.endpoint}")
        print(f"Deployment name: {self.deployment_name}")
        print(f"API version: {self.api_version}")
        print(f"Max tokens: {self.max_tokens}")
        print(f"Temperature: {self.temperature}")
        print("--------------------------------")

        # API endpoint for Azure OpenAI
        if self.endpoint:
            self.api_endpoint = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        else:
            self.api_endpoint = None
        
        # Prompt templates
        self.prompt_templates = {
            "summarize": self._get_summarize_prompt(),
            "compose_report": self._get_compose_report_prompt(),
            "analyze": self._get_analyze_prompt(),
            "generate": self._get_generate_prompt()
        }
        
        try:
            # Create Azure OpenAI client with correct parameters for v1.98.0
            client_params = {
                "api_key": self.api_key,
                "azure_endpoint": self.endpoint,
                "azure_deployment": self.deployment_name,
                "api_version": self.api_version
            }
            
            self.llm = AzureOpenAI(**client_params)
            print(f"Azure OpenAI initialized successfully. Model name: {self.deployment_name}")
        except Exception as e:
            print(f"Error initializing Azure OpenAI: {e}")
            self.llm = None
        
        if not self.api_key or not self.endpoint:
            print("--------------------------------")
            print("self.api_key: ", self.api_key)
            print("self.endpoint: ", self.endpoint)
            print("Warning: Azure OpenAI API key or endpoint not provided")
            print("--------------------------------")
        else:
            print("--------------------------------")
            print("Azure OpenAI configuration is valid")
            print("API key length:", len(self.api_key) if self.api_key else 0)
            print("Endpoint:", self.endpoint)
            print("--------------------------------")
    

    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute text generation/composition with given parameters.
        
        Args:
            parameters: Generation parameters including:
                - operation: Type of operation (summarize, compose_report, analyze, generate)
                - content: Input content for processing
                - prompt: Custom prompt (optional)
                - format: Output format (markdown, html, json, text)
                - style: Writing style (formal, casual, technical, creative)
                - length: Target length (short, medium, long)
                
        Returns:
            ToolResult with generated content
        """
        operation = parameters.get("operation", "generate")
        content = parameters.get("content", "")
        prompt = parameters.get("prompt", "")
        output_format = parameters.get("format", "text")
        style = parameters.get("style", "formal")
        length = parameters.get("length", "medium")
        
        await self.logger.info(
            f"Starting text composition",
            tool_id=self.tool_id,
            operation=operation,
            format=output_format,
            style=style
        )
        
        try:
            # Generate content
            result_content = await self._generate_content(
                operation=operation,
                content=content,
                prompt=prompt,
                format=output_format,
                style=style,
                length=length
            )
            
            return ToolResult(
                tool_id=self.tool_id,
                success=True,
                result=result_content,
                metadata={
                    "operation": operation,
                    "format": output_format,
                    "style": style,
                    "length": length,
                    "input_length": len(content),
                    "output_length": len(result_content)
                }
            )
            
        except Exception as e:
            await self.logger.error(
                f"Text composition failed",
                tool_id=self.tool_id,
                operation=operation,
                error=str(e),
                error_type=type(e).__name__,
                traceback=str(e.__traceback__) if hasattr(e, '__traceback__') else None
            )
            
            return ToolResult(
                tool_id=self.tool_id,
                success=False,
                result=None,
                metadata={
                    "operation": operation, 
                    "format": output_format,
                    "error_type": type(e).__name__
                },
                errors=[str(e)]
            )
    
    async def _generate_content(
        self,
        operation: str,
        content: str,
        prompt: str = "",
        format: str = "text",
        style: str = "formal",
        length: str = "medium"
    ) -> str:
        """
        Generate content using Azure OpenAI.
        
        Args:
            operation: Type of operation
            content: Input content
            prompt: Custom prompt
            format: Output format
            style: Writing style
            length: Target length
            
        Returns:
            Generated content
        """
        # Debug logging for configuration
        await self.logger.info(
            f"Starting content generation",
            tool_id=self.tool_id,
            operation=operation,
            has_api_key=bool(self.api_key),
            has_endpoint=bool(self.endpoint),
            has_llm=bool(self.llm),
            deployment_name=self.deployment_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        # Additional debug output
        print(f"DEBUG: api_key exists: {bool(self.api_key)}")
        print(f"DEBUG: endpoint exists: {bool(self.endpoint)}")
        print(f"DEBUG: llm exists: {bool(self.llm)}")
        print(f"DEBUG: api_key length: {len(self.api_key) if self.api_key else 0}")
        print(f"DEBUG: endpoint: {self.endpoint}")
        
        if not self.api_key or not self.endpoint:
            await self.logger.error(
                f"Missing Azure OpenAI configuration",
                tool_id=self.tool_id,
                has_api_key=bool(self.api_key),
                has_endpoint=bool(self.endpoint),
                api_key_length=len(self.api_key) if self.api_key else 0,
                endpoint_value=self.endpoint
            )
            raise Exception("Azure OpenAI API key or endpoint not provided")
        
        if not self.llm:
            await self.logger.error(
                f"Azure OpenAI client not initialized",
                tool_id=self.tool_id
            )
            raise Exception("Azure OpenAI client not initialized")
        
        # Build the prompt
        if prompt:
            system_prompt = prompt
        else:
            system_prompt = self.prompt_templates.get(operation, self.prompt_templates["generate"])
        
        # Add format and style instructions
        system_prompt += f"\n\nOutput Format: {format}\nWriting Style: {style}\nLength: {length}"
        
        # Prepare the request for Azure OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        await self.logger.info(
            f"Making Azure OpenAI request",
            tool_id=self.tool_id,
            deployment_name=self.deployment_name,
            messages_count=len(messages),
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        try:
            # Use the Azure OpenAI client directly
            response = self.llm.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            generated_text = response.choices[0].message.content
            
            await self.logger.info(
                f"Azure OpenAI request successful",
                tool_id=self.tool_id,
                response_length=len(generated_text),
                usage_tokens=response.usage.total_tokens if response.usage else None
            )
            
            return self._format_output(generated_text, format)
        
        except Exception as e:
            await self.logger.error(
                f"Azure OpenAI API failed",
                tool_id=self.tool_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise Exception(f"Azure OpenAI API error: {str(e)}")
    
    def _format_output(self, content: str, format: str) -> str:
        """Format output according to specified format."""
        if format == "markdown":
            return content
        elif format == "html":
            return f"<div>{content}</div>"
        elif format == "json":
            return json.dumps({"content": content, "timestamp": datetime.now().isoformat()})
        else:
            return content
    
 
    def _get_summarize_prompt(self) -> str:
        """Get summarization prompt template."""
        return """You are a professional summarizer. Create a concise, accurate summary of the provided content. Focus on the main points and key insights. Maintain the original meaning while making it more accessible."""
    
    def _get_compose_report_prompt(self) -> str:
        """Get report composition prompt template."""
        return """You are a professional report writer. Create a comprehensive, well-structured report based on the provided information. Include an executive summary, key findings, analysis, and conclusions. Use clear, professional language."""
    
    def _get_analyze_prompt(self) -> str:
        """Get analysis prompt template."""
        return """You are a content analyst. Analyze the provided content and provide insights about its structure, themes, sentiment, and key points. Be objective and thorough in your analysis."""
    
    def _get_generate_prompt(self) -> str:
        """Get general generation prompt template."""
        return """You are a professional content creator. Generate high-quality, relevant content based on the provided input. Be creative, informative, and engaging while maintaining accuracy and relevance."""
    
    def get_supported_operations(self) -> List[str]:
        """Get supported operation types."""
        return ["summarize", "compose_report", "analyze", "generate", "text_generation"]
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
        await super().cleanup() 