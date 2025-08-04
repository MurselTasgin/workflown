#!/usr/bin/env python3
"""
Test script to check Azure OpenAI configuration
"""

from workflown.core.config.central_config import get_config

def test_azure_config():
    """Test Azure OpenAI configuration."""
    config = get_config()
    azure_config = config.get_azure_openai_config()
    
    print("Azure OpenAI Configuration:")
    print("=" * 50)
    for key, value in azure_config.items():
        if key == "api_key":
            print(f"{key}: {'***' if value else 'None'}")
        else:
            print(f"{key}: {value}")
    
    print("\nEnvironment Variables:")
    print("=" * 50)
    import os
    azure_env_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT", 
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_MODEL_NAME",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_MAX_TOKENS",
        "AZURE_OPENAI_TEMPERATURE"
    ]
    
    for var in azure_env_vars:
        value = os.getenv(var)
        if var == "AZURE_OPENAI_API_KEY":
            print(f"{var}: {'***' if value else 'None'}")
        else:
            print(f"{var}: {value}")

if __name__ == "__main__":
    test_azure_config() 