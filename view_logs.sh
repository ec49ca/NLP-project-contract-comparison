#!/bin/bash
# View MCP server logs in real-time
# This will show all logs from the log file

if [ ! -f /tmp/mcp_server.log ]; then
    echo "Log file not found. Is the server running?"
    exit 1
fi

echo "📋 Showing MCP server logs in real-time..."
echo "Press Ctrl+C to stop viewing (server will keep running)"
echo ""
echo "=========================================="
echo ""

tail -f /tmp/mcp_server.log
