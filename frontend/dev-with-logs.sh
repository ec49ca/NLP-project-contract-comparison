#!/bin/bash
# Start frontend and show MCP server logs

# Start Next.js in background
echo "Starting Next.js frontend..."
next dev &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 2

# Check if frontend started
if ps -p $FRONTEND_PID > /dev/null; then
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
    echo ""
    echo "📋 Frontend running on http://localhost:3000"
    echo "📋 Showing MCP server logs below..."
    echo ""
    echo "=========================================="
    echo ""
    
    # Show MCP server logs in real-time (use -F to retry if file is recreated)
    tail -F /tmp/mcp_server.log
else
    echo "❌ Failed to start frontend"
    exit 1
fi

