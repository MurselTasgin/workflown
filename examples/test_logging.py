#!/usr/bin/env python3
"""
Test Script for Centralized Logging Configuration

This script demonstrates how to use the centralized logging configuration
and verifies that physical logs are properly written to files.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflown.core.logging.config import setup_logging_from_config, get_logging_summary
from workflown.core.config.central_config import get_config


async def test_logging_configuration():
    """Test the centralized logging configuration."""
    print("🔧 Testing Centralized Logging Configuration")
    print("=" * 60)
    
    # Get configuration
    config = get_config()
    logging_config = config.get_logging_config()
    
    print("📋 Current Logging Configuration:")
    for key, value in logging_config.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    
    # Set up logging
    logger = await setup_logging_from_config("test-logging")
    
    # Test different log levels
    await logger.debug("This is a debug message", test_data="debug_value")
    await logger.info("This is an info message", test_data="info_value")
    await logger.warning("This is a warning message", test_data="warning_value")
    await logger.error("This is an error message", test_data="error_value")
    await logger.critical("This is a critical message", test_data="critical_value")
    
    # Test structured logging with context
    await logger.info("Testing structured logging", 
                     user_id="test_user",
                     session_id="test_session_001",
                     workflow_id="test_workflow_001",
                     task_id="test_task_001",
                     execution_time=1.234,
                     success=True)
    
    # Test performance metrics
    await logger.performance_metric("response_time", 0.045, "seconds")
    await logger.performance_metric("memory_usage", 128.5, "MB")
    
    # Test audit logging
    await logger.audit_log("data_access", "user_profile", "test_user")
    await logger.audit_log("workflow_execution", "web_research", "test_user")
    
    print("\n✅ Logging test completed!")
    print("📂 Check the following log files:")
    
    # Show logging summary
    summary = get_logging_summary()
    if summary["handlers"]["file"]:
        print(f"  📄 Main logs: {summary['file_paths']['main']}")
    if summary["handlers"]["structured"]:
        print(f"  📄 Structured logs: {summary['file_paths']['structured']}")
    
    return logger


async def test_log_file_creation():
    """Test that log files are actually created."""
    print("\n🔍 Testing Log File Creation")
    print("=" * 60)
    
    # Get configuration
    config = get_config()
    logging_config = config.get_logging_config()
    
    # Check if file logging is enabled
    if not logging_config.get("enable_file", True):
        print("❌ File logging is disabled in configuration")
        return
    
    # Get log file paths
    main_log_path = Path(logging_config.get("file_path", "./logs/workflown.log"))
    structured_log_path = Path(logging_config.get("structured_file_path", "./logs/workflown-structured.log"))
    
    print(f"📄 Main log file: {main_log_path}")
    print(f"📄 Structured log file: {structured_log_path}")
    
    # Check if files exist
    if main_log_path.exists():
        size = main_log_path.stat().st_size
        print(f"✅ Main log file exists (size: {size} bytes)")
    else:
        print("❌ Main log file does not exist")
    
    if structured_log_path.exists():
        size = structured_log_path.stat().st_size
        print(f"✅ Structured log file exists (size: {size} bytes)")
    else:
        print("❌ Structured log file does not exist")
    
    # Show last few lines of main log file
    if main_log_path.exists():
        print(f"\n📖 Last 5 lines of {main_log_path.name}:")
        try:
            with open(main_log_path, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    print(f"  {line.rstrip()}")
        except Exception as e:
            print(f"  Error reading log file: {e}")


async def main():
    """Main test function."""
    print("🚀 Workflown Logging Configuration Test")
    print("=" * 60)
    
    try:
        # Test logging configuration
        logger = await test_logging_configuration()
        
        # Test log file creation
        await test_log_file_creation()
        
        print("\n✨ All tests completed successfully!")
        print("📂 Log files should be created in the configured directories")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 