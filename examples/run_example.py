#!/usr/bin/env python3
"""
Simple Runner for Web Research Workflow Example

This script demonstrates how to run the web research workflow with different configurations.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_research_workflow import main as run_web_research


async def run_basic_example():
    """Run the basic web research example."""
    print("🔍 Running Basic Web Research Example")
    print("Query: 'artificial intelligence machine learning'")
    print("Format: Markdown")
    print("-" * 50)
    
    await run_web_research()


async def run_custom_example():
    """Run a custom example with different parameters."""
    print("🔍 Running Custom Web Research Example")
    print("Query: 'machine learning applications'")
    print("Format: HTML")
    print("-" * 50)
    
    # Import the workflow components
    from web_research_workflow import WebResearchWorkflow, setup_logging
    
    # Set up logging
    logger = await setup_logging()
    await logger.info("=== CUSTOM WORKFLOWN EXAMPLE STARTED ===")
    
    try:
        # Create workflow with custom configuration
        workflow = WebResearchWorkflow(
            workflow_id="custom-research-001",
            config={"timeout": 300}  # 5 minute timeout
        )
        
        await workflow.setup()
        
        # Custom research context
        custom_context = {
            "query": "machine learning applications in healthcare",
            "max_results": 2,
            "summary_type": "brief",
            "output_format": "html",
            "user_id": "custom_user",
            "session_id": "custom_session_001"
        }
        
        # Execute workflow
        result = await workflow.execute(custom_context)
        
        # Display results
        print("\n" + "=" * 50)
        print("🎉 CUSTOM WORKFLOW COMPLETED")
        print("=" * 50)
        
        if result.success:
            print(f"✅ Success in {result.execution_time:.2f}s")
            if "final_report" in result.result:
                # Save HTML report to file
                report_file = Path("./examples/data/custom_report.html")
                report_file.parent.mkdir(parents=True, exist_ok=True)
                with open(report_file, 'w') as f:
                    f.write(result.result["final_report"])
                print(f"📄 HTML report saved to: {report_file}")
        else:
            print(f"❌ Failed: {result.errors}")
        
        await workflow.cleanup()
        
    except Exception as e:
        await logger.error("Custom example failed", exception=e)
        print(f"❌ Custom example failed: {e}")


async def main():
    """Main function to run examples."""
    print("🚀 Workflown Framework - Web Research Examples")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "custom":
        await run_custom_example()
    else:
        await run_basic_example()
    
    print("\n✨ Examples completed!")
    print("📂 Check ./examples/logs/ for detailed logs")
    print("📂 Check ./examples/data/ for stored results")


if __name__ == "__main__":
    asyncio.run(main())