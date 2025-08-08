#!/usr/bin/env python3
"""
Test Metadata Extraction

Tests the automatic metadata extraction functionality.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add workflown to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.tools.base_tool import BaseTool, ToolResult, ToolCapability
from workflown.core.tools.tool_registry import ToolRegistry


class TestTool(BaseTool):
    """Test tool for metadata extraction."""
    
    def __init__(self, tool_id: str = None, config: Dict[str, Any] = None):
        super().__init__(
            tool_id=tool_id or "test_tool",
            name="TestTool",
            description="A test tool for metadata extraction",
            capabilities=[ToolCapability.DATA_PROCESSING, ToolCapability.CUSTOM],
            config=config or {}
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the test tool."""
        return ToolResult(
            tool_id=self.tool_id,
            success=True,
            result={"test": "result"}
        )
    
    def get_supported_operations(self) -> List[str]:
        return ["test_operation", "data_processing"]
    
    def get_version(self) -> str:
        return "2.0.0"
    
    def get_author(self) -> str:
        return "Test Author"
    
    def get_tags(self) -> List[str]:
        return ["test", "metadata", "extraction"]
    
    def _get_required_parameters(self) -> List[str]:
        return ["input"]
    
    def _get_optional_parameters(self) -> List[str]:
        return ["output", "format"]
    
    def _get_parameter_descriptions(self) -> Dict[str, str]:
        return {
            "input": "Input data to process",
            "output": "Output format",
            "format": "Data format"
        }
    
    def _get_parameter_types(self) -> Dict[str, str]:
        return {
            "input": "string",
            "output": "string",
            "format": "string"
        }


async def test_metadata_extraction():
    """Test automatic metadata extraction."""
    
    print("🧪 Testing Metadata Extraction")
    print("=" * 40)
    
    # Create test tool
    tool = TestTool()
    
    # Test metadata extraction
    metadata = tool.get_metadata()
    print("📋 Extracted Metadata:")
    for key, value in metadata.items():
        print(f"   • {key}: {value}")
    
    # Test parameter extraction
    parameters = tool.get_parameters()
    print("\n📋 Extracted Parameters:")
    for key, value in parameters.items():
        print(f"   • {key}: {value}")
    
    # Test registry registration
    registry = ToolRegistry()
    tool_id = registry.register_tool_class(TestTool)
    
    print(f"\n✅ Registered tool with ID: {tool_id}")
    
    # Verify registration worked
    stats = registry.get_statistics()
    print(f"📊 Registry stats: {stats['total_tools']} tools registered")
    
    # Test tool instance creation
    instance = registry.create_tool_instance(tool_id, "test_instance")
    if instance:
        print("✅ Tool instance created successfully")
        
        # Test execution
        result = await instance.execute_with_tracking({"input": "test"})
        if result.success:
            print("✅ Tool execution successful")
        else:
            print("❌ Tool execution failed")
    else:
        print("❌ Failed to create tool instance")
    
    # Cleanup
    await registry.cleanup_all_instances()
    print("✅ Cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_metadata_extraction()) 