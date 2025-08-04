# Azure OpenAI Setup Guide

This guide explains how to configure Azure OpenAI for the ComposerTool.

## Prerequisites

1. Azure subscription
2. Azure OpenAI service deployed
3. API key and endpoint from your Azure OpenAI resource

## Configuration

### 1. Create .env file

Create a `.env` file in the project root with the following Azure OpenAI configuration:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MAX_TOKENS=2000
AZURE_OPENAI_TEMPERATURE=0.7
```

### 2. Get Azure OpenAI Credentials

1. Go to the Azure Portal
2. Navigate to your Azure OpenAI resource
3. Go to "Keys and Endpoint" section
4. Copy the API key and endpoint URL

### 3. Update Configuration

Replace the placeholder values in your `.env` file:

- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint (e.g., `https://myresource.openai.azure.com`)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Your deployment name (e.g., `gpt-35-turbo`)

## Testing Configuration

Run the test script to verify your Azure OpenAI configuration:

```bash
conda activate cenv312
python examples/test_tools.py
```

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your API key is correct and has proper permissions
2. **Endpoint Error**: Verify the endpoint URL is correct and includes the full path
3. **Deployment Not Found**: Check that the deployment name exists in your Azure OpenAI resource
4. **Rate Limiting**: Azure OpenAI has rate limits; check your usage in the Azure portal

### Debug Mode

Enable debug mode to see detailed logs:

```bash
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

## Security Notes

- Never commit your `.env` file to version control
- Use environment variables in production
- Rotate API keys regularly
- Monitor usage in Azure portal

## Example Usage

```python
from tools import ComposerTool

# Create composer tool (will use Azure OpenAI config from .env)
composer = ComposerTool()

# Use the tool
result = await composer.execute_with_tracking({
    "operation": "summarize",
    "content": "Your content here...",
    "format": "text",
    "style": "formal"
})
``` 