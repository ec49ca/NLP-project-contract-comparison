#!/bin/bash
# Start MCP server and show logs in terminal

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Kill any existing server
echo "Stopping any existing MCP server..."
ps aux | grep "uvicorn.*mcp_server" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null
sleep 1

# Clear old log file
> /tmp/mcp_server.log

# Start server in background with unbuffered output (-u flag)
echo "Starting MCP server..."
python3 -u -m uvicorn src.server.mcp_server:app --host 0.0.0.0 --port 8000 --log-level info >> /tmp/mcp_server.log 2>&1 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Check if server started successfully
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ MCP server started (PID: $SERVER_PID)"
    echo "📋 Showing all logs in real-time. Press Ctrl+C to stop (server will keep running)."
    echo "   To stop the server: kill $SERVER_PID"
    echo ""
    echo "=========================================="
    echo ""
    
    # Show logs in real-time (including existing content)
    tail -f /tmp/mcp_server.log
else
    echo "❌ Failed to start server. Check /tmp/mcp_server.log for errors."
    exit 1
fi
