#!/usr/bin/env python3
"""
Command Line Interface for Workflown

Provides a simple CLI for running workflows and managing the framework.
"""

import argparse
import asyncio
import sys
from typing import Optional
from pathlib import Path

from .core.config.central_config import CentralConfig
from .core.execution.executor_registry import ExecutorRegistry
from .core.workflows.base_workflow import BaseWorkflow


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Workflown - A modular workflow execution framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  workflown run examples/web_research_workflow.py
  workflown list-executors
  workflown --version
        """
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version="workflown 0.1.0"
    )
    
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("workflow", help="Path to workflow file or workflow name")
    run_parser.add_argument("--params", type=str, help="JSON string of workflow parameters")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available workflows")
    
    # Executors command
    executors_parser = subparsers.add_parser("list-executors", help="List available executors")
    
    return parser


async def run_workflow(workflow_path: str, params: Optional[str] = None) -> int:
    """Run a workflow from file."""
    try:
        # Load configuration
        config = CentralConfig()
        
        # Initialize executor registry
        registry = ExecutorRegistry()
        
        # Load and run workflow
        workflow_file = Path(workflow_path)
        if not workflow_file.exists():
            print(f"Error: Workflow file '{workflow_path}' not found")
            return 1
        
        # Import the workflow module
        import importlib.util
        spec = importlib.util.spec_from_file_location("workflow", workflow_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find workflow class
        workflow_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, BaseWorkflow) and 
                attr != BaseWorkflow):
                workflow_class = attr
                break
        
        if not workflow_class:
            print("Error: No workflow class found in the file")
            return 1
        
        # Parse parameters
        workflow_params = {}
        if params:
            import json
            workflow_params = json.loads(params)
        
        # Create and run workflow
        workflow = workflow_class(**workflow_params)
        result = await workflow.run()
        
        if result.success:
            print("✅ Workflow completed successfully")
            return 0
        else:
            print("❌ Workflow failed")
            return 1
            
    except Exception as e:
        print(f"Error running workflow: {e}")
        return 1


async def list_workflows() -> int:
    """List available workflows."""
    try:
        # This would scan for available workflows
        print("Available workflows:")
        print("  - examples/web_research_workflow.py")
        print("  - examples/run_example.py")
        return 0
    except Exception as e:
        print(f"Error listing workflows: {e}")
        return 1


async def list_executors() -> int:
    """List available executors."""
    try:
        registry = ExecutorRegistry()
        executors = registry.get_all_executors()
        
        if not executors:
            print("No executors registered")
            return 0
        
        print("Available executors:")
        for executor in executors:
            print(f"  - {executor.name} ({executor.executor_id})")
            print(f"    Description: {executor.description}")
            print(f"    Capabilities: {', '.join(executor.capabilities)}")
            print()
        
        return 0
    except Exception as e:
        print(f"Error listing executors: {e}")
        return 1


async def main_async() -> int:
    """Main async function."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up logging
    if args.log_level:
        import logging
        logging.basicConfig(level=getattr(logging, args.log_level))
    
    # Load configuration
    if args.config:
        # TODO: Load custom config
        pass
    
    # Handle commands
    if args.command == "run":
        return await run_workflow(args.workflow, args.params)
    elif args.command == "list":
        return await list_workflows()
    elif args.command == "list-executors":
        return await list_executors()
    else:
        parser.print_help()
        return 0


def main() -> int:
    """Main entry point."""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 