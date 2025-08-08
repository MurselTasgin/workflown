#!/usr/bin/env python3
"""
Simple test script to demonstrate real-time workflow execution.
"""

import asyncio
import sys
from pathlib import Path

# Add workflown to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.test_workflown_workflow import GenericWorkflowExample

async def test_realtime_workflow():
    """Test the real-time workflow execution."""
    
    print("🧪 Testing Real-time Workflow Execution")
    print("=" * 60)
    
    # Create workflow with a simple query
    workflow_config = {
        "query": "Python async programming",
        "max_tasks": 3,
        "task_types": ["web_search", "webpage_parse", "compose"]
    }
    
    workflow = GenericWorkflowExample(config=workflow_config)
    
    # Execute workflow
    context = {"query": "Python async programming"}
    result = await workflow.execute(context)
    
    if result.success:
        print("\n✅ Test completed successfully!")
        print(f"Execution time: {result.execution_time:.2f} seconds")
    else:
        print("\n❌ Test failed!")
        print(f"Errors: {result.errors}")
    
    return 0 if result.success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_realtime_workflow())
    sys.exit(exit_code) 