# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Workflown is a Python-based workflow and task scheduling framework that provides intelligent task dispatching, event-driven communication, and configurable agent orchestration. The system is designed around a modular architecture with clear separation of concerns.

## Architecture

### Core Components

**Configuration Management** (`workflown/core/config/`)
- `CentralConfig`: Centralized configuration management with environment variable support, YAML file loading, and validation
- Supports Azure OpenAI integration with comprehensive configuration specifications
- Configuration keys use dot notation (e.g., `azure_openai.api_key`)

**Event System** (`workflown/core/events/`)
- `EventBus`: Asynchronous event-driven communication between components
- Supports both sync and async event handlers with priority levels
- Event types are defined in `event_types.py`, listeners in `listeners.py`

**Task Dispatching** (`workflown/core/dispatch/`)
- `TaskDispatcher`: Intelligent task assignment to agents based on capabilities, load balancing, and optimization strategies
- Multiple dispatch strategies: CAPABILITY_MATCH, LOAD_BALANCE, PRIORITY_FIRST, ROUND_ROBIN, OPTIMAL_ASSIGNMENT
- Agent suitability scoring considers capability matching (40%), load balancing (20%), performance history (20%), task preferences (10%), and agent type matching (10%)

**Workflow Management** (`workflown/core/workflows/`)
- `BaseWorkflow`: Abstract base class for workflow orchestration
- Workflow states: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED
- `ExecutionContext` and `Task` classes support complex workflow execution patterns

### Key Design Patterns

1. **Factory Pattern**: `ComponentFactory` for creating configured components
2. **Registry Pattern**: Agent registry for managing available agents
3. **Strategy Pattern**: Multiple dispatch strategies for different scenarios
4. **Observer Pattern**: Event bus for loose coupling between components
5. **Configuration Pattern**: Centralized configuration with validation and type conversion

## Development Setup

This is a Python project without apparent package management files (no `setup.py`, `pyproject.toml`, or `requirements.txt` found). To work with this codebase:

```bash
# Install dependencies manually based on imports found:
pip install pyyaml python-dotenv

# The project expects configuration files in a `config/` directory
# Environment variables can be loaded from a `.env` file
```

### Required Environment Variables

For Azure OpenAI integration:
- `AZURE_OPENAI_API_KEY`: Required API key
- `AZURE_OPENAI_ENDPOINT`: Required endpoint URL  
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Required deployment name
- `AZURE_OPENAI_API_VERSION`: Optional (defaults to "2024-02-15-preview")
- `AZURE_OPENAI_TEMPERATURE`: Optional (defaults to 0.7)
- `AZURE_OPENAI_MAX_TOKENS`: Optional (defaults to 1000)

Framework configuration:
- `DEBUG_MODE`: Enable debug mode (boolean)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `MAX_CONCURRENT_TASKS`: Maximum concurrent tasks (default: 10)

## Configuration

The system expects YAML configuration files in a `config/` directory:
- `default.yaml` - Base configuration
- `models.yaml` - Model configurations  
- `agents.yaml` - Agent configurations
- `tools.yaml` - Tool configurations
- `storage.yaml` - Storage configurations

Configuration uses dot notation for nested values and supports environment variable overrides.

## Testing

No test framework configuration was found in the codebase. When adding tests, determine the testing approach by examining the project structure or asking the user for their preferred testing framework.