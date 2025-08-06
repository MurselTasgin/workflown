#!/usr/bin/env python3
"""
Demonstration of Generic Workflow Execution Engine

This script shows how the WorkflowExecutionEngine can be used to create
different types of workflows without hardcoding task execution logic.
"""

import asyncio
import sys
from pathlib import Path

# Add workflown to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent / "tools" / "websearch"))

from test_workflown_workflow import SearchScrapeSummarizeWorkflow, DataAnalysisWorkflow


async def demo_search_workflow():
    """Demonstrate the search-scrape-summarize workflow."""
    print("🔍 DEMO: Search-Scrape-Summarize Workflow")
    print("=" * 50)
    
    workflow_config = {
        "query": "Quantum computing applications 2025",
        "max_urls": 3,
        "scrape_limit": 2
    }
    
    workflow = SearchScrapeSummarizeWorkflow(config=workflow_config)
    result = await workflow.execute({"query": "Quantum computing applications 2025"})
    
    if result.success:
        print(f"✅ Search workflow completed successfully!")
        print(f"📊 Execution time: {result.execution_time:.2f} seconds")
        print(f"📋 Summary length: {len(str(result.result.get('final_summary', '')))} characters")
    else:
        print(f"❌ Search workflow failed: {result.errors}")
    
    print()


async def demo_data_analysis_workflow():
    """Demonstrate the data analysis workflow."""
    print("📊 DEMO: Data Analysis Workflow")
    print("=" * 50)
    
    workflow_config = {
        "dataset_path": "financial_data.csv",
        "analysis_type": "trend_analysis"
    }
    
    workflow = DataAnalysisWorkflow(config=workflow_config)
    result = await workflow.execute({"dataset_path": "financial_data.csv"})
    
    if result.success:
        print(f"✅ Data analysis workflow completed successfully!")
        print(f"📊 Execution time: {result.execution_time:.2f} seconds")
        print(f"📈 Analysis type: {result.result.get('analysis_type', 'unknown')}")
    else:
        print(f"❌ Data analysis workflow failed: {result.errors}")
    
    print()


async def demo_workflow_comparison():
    """Compare different workflow types using the same execution engine."""
    print("🔄 DEMO: Workflow Comparison")
    print("=" * 50)
    
    workflows = [
        {
            "name": "Search Workflow",
            "class": SearchScrapeSummarizeWorkflow,
            "config": {"query": "AI trends 2025", "max_urls": 2, "scrape_limit": 1}
        },
        {
            "name": "Data Analysis Workflow", 
            "class": DataAnalysisWorkflow,
            "config": {"dataset_path": "sales_data.csv", "analysis_type": "correlation_analysis"}
        }
    ]
    
    results = []
    
    for workflow_info in workflows:
        print(f"🚀 Running {workflow_info['name']}...")
        
        workflow = workflow_info["class"](config=workflow_info["config"])
        result = await workflow.execute({})
        
        results.append({
            "name": workflow_info["name"],
            "success": result.success,
            "execution_time": result.execution_time,
            "tasks_executed": result.metadata.get("tasks_executed", 0)
        })
        
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        print(f"   {status} - {result.execution_time:.2f}s - {result.metadata.get('tasks_executed', 0)} tasks")
    
    print(f"\n📊 Summary:")
    successful = sum(1 for r in results if r["success"])
    total_time = sum(r["execution_time"] for r in results)
    total_tasks = sum(r["tasks_executed"] for r in results)
    
    print(f"   • Workflows completed: {successful}/{len(results)}")
    print(f"   • Total execution time: {total_time:.2f} seconds")
    print(f"   • Total tasks executed: {total_tasks}")


async def main():
    """Run all demonstrations."""
    print("🚀 Generic Workflow Execution Engine Demonstrations")
    print("=" * 60)
    print()
    
    try:
        # Demo 1: Search workflow
        await demo_search_workflow()
        
        # Demo 2: Data analysis workflow  
        await demo_data_analysis_workflow()
        
        # Demo 3: Workflow comparison
        await demo_workflow_comparison()
        
        print("🎉 All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 