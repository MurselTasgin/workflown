# Azure OpenAI Setup Guide

This guide explains how to configure Azure OpenAI services for the workflown framework.

## Prerequisites

1. **Azure OpenAI Resource**: You need an Azure OpenAI resource deployed in your Azure subscription
2. **API Key**: Your Azure OpenAI API key
3. **Deployment**: A model deployment (e.g., GPT-4o-mini) in your Azure OpenAI resource

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Required Azure OpenAI settings
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_MODEL_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional settings
AZURE_OPENAI_MAX_TOKENS=2000
AZURE_OPENAI_TEMPERATURE=0.7
```

### 2. Azure OpenAI Resource Setup

1. **Create Azure OpenAI Resource**:
   - Go to Azure Portal
   - Create a new "Azure OpenAI" resource
   - Choose your subscription and resource group
   - Select a region close to you
   - Choose a pricing tier

2. **Deploy a Model**:
   - Go to your Azure OpenAI resource
   - Navigate to "Model deployments"
   - Click "Manage deployments"
   - Add a new deployment (e.g., GPT-4o-mini)
   - Note the deployment name

3. **Get API Key**:
   - Go to "Keys and Endpoint" in your Azure OpenAI resource
   - Copy the API key (Key 1 or Key 2)
   - Copy the endpoint URL

### 3. Configuration Values

Replace the placeholder values in your `.env` file:

- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL (e.g., `https://your-resource.openai.azure.com/`)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: The name of your model deployment
- `AZURE_OPENAI_MODEL_NAME`: The model name (e.g., `gpt-4o-mini`, `gpt-4`, `gpt-35-turbo`)

## Usage

The LLM tool will automatically use the Azure OpenAI configuration from the central config. You can also override settings when creating the tool:

```python
from tools.llm_tool import LLMTool

# Use default configuration from .env
llm_tool = LLMTool()

# Or override specific settings
llm_tool = LLMTool(config={
    "max_tokens": 3000,
    "temperature": 0.5
})
```

## Testing

Run the test workflow to verify your Azure OpenAI setup:

```bash
cd examples
python test_simple_workflow.py
```

## Troubleshooting

### Common Issues

1. **"Missing required Azure OpenAI configuration"**:
   - Check that all required environment variables are set
   - Verify the `.env` file is in the correct location

2. **"Failed to initialize Azure OpenAI client"**:
   - Verify your API key is correct
   - Check that your endpoint URL is valid
   - Ensure your deployment name exists

3. **"openai package not installed"**:
   - Install the OpenAI package: `pip install openai`

4. **Authentication errors**:
   - Verify your API key has the correct permissions
   - Check that your Azure OpenAI resource is active

### Debug Mode

Enable debug mode to see more detailed error messages:

```bash
DEBUG_MODE=true python test_simple_workflow.py
```

## Security Notes

- Never commit your `.env` file to version control
- Use environment variables in production
- Consider using Azure Key Vault for production deployments
- Rotate your API keys regularly

## Cost Optimization

- Use appropriate model sizes for your use case
- Monitor your token usage
- Set reasonable `max_tokens` limits
- Consider using caching for repeated requests 