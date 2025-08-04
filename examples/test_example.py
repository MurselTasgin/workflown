"""
Test Script for Web Research Workflow Example

Quick validation that the example works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.logging.logger import get_logger, LogLevel
from workflown.core.logging.handlers import ConsoleHandler
from workflown.core.logging.formatters import StandardFormatter
from web_research_workflow import WebSearchExecutor, SummarizerExecutor, ComposerExecutor
from workflown.core.workflows.task import Task


async def test_executors():
    """Test individual executors."""
    print("🧪 Testing Individual Executors")
    print("-" * 40)
    
    # Set up basic logging
    logger = get_logger("test", LogLevel.INFO)
    console_handler = ConsoleHandler()
    console_handler.set_formatter(StandardFormatter())
    logger.add_handler(console_handler)
    
    try:
        # Test Web Search Executor
        print("1. Testing WebSearchExecutor...")
        web_executor = WebSearchExecutor("test-web-1")
        await web_executor.start()
        
        search_task = Task(
            task_id="test-search",
            name="Test Search",
            task_type="web_search", 
            parameters={"query": "test query", "max_results": 2}
        )
        
        search_result = await web_executor.execute_task(search_task)
        print(f"   ✅ Search found {search_result['total_results']} results")
        
        # Test Summarizer Executor
        print("2. Testing SummarizerExecutor...")
        summarizer = SummarizerExecutor("test-summarizer-1")
        await summarizer.start()
        
        summary_task = Task(
            task_id="test-summary",
            name="Test Summary",
            task_type="summarize",
            parameters={
                "search_results": search_result,
                "summary_type": "brief"
            }
        )
        
        summary_result = await summarizer.execute_task(summary_task)
        print(f"   ✅ Summary created: {summary_result['character_count']} characters")
        
        # Test Composer Executor
        print("3. Testing ComposerExecutor...")
        composer = ComposerExecutor("test-composer-1")
        await composer.start()
        
        compose_task = Task(
            task_id="test-compose",
            name="Test Compose",
            task_type="compose",
            parameters={
                "summary_data": summary_result,
                "format": "markdown"
            }
        )
        
        compose_result = await composer.execute_task(compose_task)
        print(f"   ✅ Report composed: {compose_result['character_count']} characters")
        
        # Clean up
        await web_executor.stop()
        await summarizer.stop()
        await composer.stop()
        
        print("\n🎉 All executor tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Executor test failed: {e}")
        return False


async def test_workflow_components():
    """Test workflow component initialization."""
    print("\n🧪 Testing Workflow Components")
    print("-" * 40)
    
    try:
        from web_research_workflow import WebResearchWorkflow
        
        # Create workflow
        workflow = WebResearchWorkflow("test-workflow-001")
        
        # Test setup
        print("1. Testing workflow setup...")
        await workflow.setup()
        print("   ✅ Workflow setup successful")
        
        # Test component access
        print("2. Testing component access...")
        assert workflow.storage is not None, "Storage not initialized"
        assert workflow.event_bus is not None, "Event bus not initialized"
        assert workflow.executor_registry is not None, "Executor registry not initialized"
        assert workflow.planner is not None, "Planner not initialized"
        assert workflow.dispatcher is not None, "Dispatcher not initialized"
        print("   ✅ All components accessible")
        
        # Test executor registration
        print("3. Testing executor registration...")
        executors = workflow.executor_registry.get_all_executors()
        assert len(executors) >= 3, f"Expected at least 3 executors, got {len(executors)}"
        print(f"   ✅ {len(executors)} executors registered")
        
        # Test storage connectivity
        print("4. Testing storage connectivity...")
        assert workflow.storage.is_connected, "Storage not connected"
        health = await workflow.storage.health_check()
        assert health["healthy"], "Storage health check failed"
        print("   ✅ Storage healthy")
        
        # Clean up
        await workflow.cleanup()
        print("   ✅ Cleanup successful")
        
        print("\n🎉 All component tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Workflown Example Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test executors
    success &= await test_executors()
    
    # Test workflow components  
    success &= await test_workflow_components()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ ALL TESTS PASSED - Example is ready to run!")
        print("\nNext steps:")
        print("  python run_example.py          # Run basic example")
        print("  python run_example.py custom   # Run custom example")
        print("  python web_research_workflow.py # Run full workflow")
    else:
        print("❌ SOME TESTS FAILED - Check the output above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())