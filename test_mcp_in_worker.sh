#!/bin/bash
# Script to test MCP access in Cloud Run worker

echo "🧪 Testing MCP access in Cloud Run worker environment..."
echo "Current working directory: $(pwd)"
echo "Python path: $(which python)"
echo "Available files:"
ls -la

echo ""
echo "🐍 Running MCP test..."
python test_mcp_worker.py
