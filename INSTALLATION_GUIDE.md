# Workflown Installation Guide

## Overview

This guide explains how to install and use the Workflown package in development mode with the conda environment `cenv312`.

## Prerequisites

- Conda installed on your system
- Python 3.12 (provided by cenv312 environment)

## Quick Installation

### 1. Activate the conda environment

```bash
conda activate cenv312
```

### 2. Install the package in development mode

```bash
pip install -e .
```

### 3. Verify installation

```bash
python -c "import workflown; print('✅ Package installed successfully')"
workflown --version
```

## Development Tools

### Using the Makefile

The project includes a `Makefile` with common development tasks:

```bash
# Show all available commands
make help

# Install in development mode
make install

# Install with development dependencies
make install-dev

# Test CLI functionality
make cli-test

# Check package structure
make check

# Run example workflow
make example
```

### Using the activation script

For convenience, use the `activate_env.sh` script:

```bash
# Test CLI
./activate_env.sh workflown --help

# Run Python scripts
./activate_env.sh python examples/test_example.py

# Install dependencies
./activate_env.sh pip install -e .
```

## Package Structure

The following files have been created for proper package installation:

- `setup.py` - Package setup configuration
- `pyproject.toml` - Modern Python packaging configuration
- `requirements.txt` - Basic dependencies
- `MANIFEST.in` - Files to include in distribution
- `workflown/__init__.py` - Main package initialization
- `workflown/cli.py` - Command-line interface
- `LICENSE` - MIT license
- `README.md` - Comprehensive documentation
- `.gitignore` - Git ignore patterns
- `Makefile` - Development tasks
- `activate_env.sh` - Conda environment activation script

## CLI Usage

Once installed, you can use the `workflown` command:

```bash
# Show help
workflown --help

# Show version
workflown --version

# List available executors
workflown list-executors

# List available workflows
workflown list

# Run a workflow
workflown run examples/web_research_workflow.py
```

## Development Workflow

1. **Always activate the conda environment**:
   ```bash
   conda activate cenv312
   ```

2. **Install in development mode**:
   ```bash
   pip install -e .
   ```

3. **Use the Makefile for common tasks**:
   ```bash
   make help          # Show available commands
   make cli-test      # Test CLI functionality
   make check         # Verify package structure
   ```

4. **Use the activation script for convenience**:
   ```bash
   ./activate_env.sh python your_script.py
   ```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure:

1. The conda environment is activated: `conda activate cenv312`
2. The package is installed: `pip install -e .`
3. You're running Python from the correct environment

### CLI Not Found

If the `workflown` command is not found:

1. Verify installation: `pip list | grep workflown`
2. Check the installation: `pip show workflown`
3. Reinstall if needed: `pip install -e .`

### Environment Issues

If conda activation fails:

1. Initialize conda: `conda init`
2. Restart your terminal
3. Try activating again: `conda activate cenv312`

## Package Information

- **Name**: workflown
- **Version**: 0.1.0
- **Python Version**: >=3.8
- **License**: MIT
- **Author**: Workflown Team

## Next Steps

1. Explore the examples in the `examples/` directory
2. Read the comprehensive documentation in `README.md`
3. Check out the core modules in `workflown/core/`
4. Start building your own workflows!

## Support

For issues or questions:

1. Check the `README.md` for comprehensive documentation
2. Review the examples in the `examples/` directory
3. Check the package structure in `workflown/` directory 