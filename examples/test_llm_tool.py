#!/usr/bin/env python3
"""
Test script for LLM Tool with Azure OpenAI.

Tests the LLM tool with GPT-4o-mini model using Azure OpenAI.
Requires Azure OpenAI API key and endpoint configuration.

Usage:
    python examples/test_llm_tool.py

Requirements:
    pip install openai
"""

import asyncio
import sys
from pathlib import Path

# Add the tools directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

try:
    from llm_tool import LLMTool
except ImportError as e:
    print(f"Error importing LLMTool: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


async def test_text_completion():
    """Test basic text completion."""
    print("🔤 Testing Text Completion")
    print("=" * 50)
    
    tool = LLMTool()
    
    try:
        result = await tool.execute({
            "prompt": "Explain the concept of agentic AI frameworks in 2-3 sentences.",
            "max_tokens": 200,
            "temperature": 0.7,
            "operation_type": "completion"
        })
        
        if result.success:
            print("✅ Text completion successful")
            print(f"Result: {result.result}")
            print(f"Execution time: {result.execution_time:.2f}s")
        else:
            print(f"❌ Text completion failed: {result.errors}")
        
        await tool.cleanup()
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")


async def test_chat_completion():
    """Test chat completion."""
    print("\n💬 Testing Chat Completion")
    print("=" * 50)
    
    tool = LLMTool()
    
    try:
        result = await tool.execute({
            "messages": [
                {"role": "user", "content": "What are the main benefits of using agentic AI frameworks?"}
            ],
            "system_prompt": "You are a helpful AI assistant that provides concise and accurate information.",
            "max_tokens": 300,
            "temperature": 0.5,
            "operation_type": "chat"
        })
        
        if result.success:
            print("✅ Chat completion successful")
            print(f"Result: {result.result}")
            print(f"Execution time: {result.execution_time:.2f}s")
        else:
            print(f"❌ Chat completion failed: {result.errors}")
        
        await tool.cleanup()
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")


async def test_summarization():
    """Test text summarization."""
    print("\n📝 Testing Text Summarization")
    print("=" * 50)
    
    tool = LLMTool()
    
    long_text = """
    Agentic AI frameworks represent a significant advancement in artificial intelligence, 
    enabling AI systems to operate with greater autonomy and decision-making capabilities. 
    These frameworks provide the infrastructure for AI agents to perceive their environment, 
    make decisions, and take actions to achieve specific goals. Unlike traditional AI systems 
    that require explicit programming for every scenario, agentic AI frameworks allow for 
    more flexible and adaptive behavior. They typically include components for task planning, 
    memory management, tool usage, and learning from experience. This approach is particularly 
    valuable in complex, dynamic environments where predefined rules may not be sufficient 
    to handle all possible situations.
    """
    
    try:
        result = await tool.execute({
            "prompt": long_text,
            "max_tokens": 150,
            "temperature": 0.3,
            "operation_type": "summarize"
        })
        
        if result.success:
            print("✅ Summarization successful")
            print(f"Summary: {result.result}")
            print(f"Execution time: {result.execution_time:.2f}s")
        else:
            print(f"❌ Summarization failed: {result.errors}")
        
        await tool.cleanup()
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")


async def test_model_info():
    """Test getting model information."""
    print("\nℹ️  Testing Model Information")
    print("=" * 50)
    
    tool = LLMTool()
    
    try:
        model_info = tool.get_model_info()
        print("✅ Model information retrieved")
        print(f"Model: {model_info.get('model_name')}")
        print(f"Deployment: {model_info.get('deployment_name')}")
        print(f"Endpoint: {model_info.get('endpoint')}")
        print(f"API Version: {model_info.get('api_version')}")
        print(f"Max Tokens: {model_info.get('max_tokens')}")
        print(f"Temperature: {model_info.get('temperature')}")
        
        await tool.cleanup()
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")


async def main():
    """Run all LLM tool tests."""
    print("🤖 LLM Tool Test Suite")
    print("=" * 60)
    print("Testing Azure OpenAI with GPT-4o-mini")
    print("=" * 60)
    
    try:
        # Test model information first
        await test_model_info()
        
        # Test different operations
        await test_text_completion()
        await test_chat_completion()
        await test_summarization()
        
        print("\n🏁 All tests completed!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test suite interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 