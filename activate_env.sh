#!/bin/bash
# Script to activate conda environment and run Python commands

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate cenv312

# Run the command passed as arguments
if [ $# -eq 0 ]; then
    echo "Usage: ./activate_env.sh <command>"
    echo "Examples:"
    echo "  ./activate_env.sh python examples/test_example.py"
    echo "  ./activate_env.sh workflown --help"
    echo "  ./activate_env.sh pip install -e ."
    exit 1
fi

# Execute the command
"$@" 