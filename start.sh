#!/bin/bash
# Start backend and frontend together

PROJECT="/Users/chaitanyarajkumar/cursor_projects/vetty-voice-platform"

echo ""
echo "  Starting AgentForge Platform..."
echo ""

# Start backend
cd "$PROJECT"
/opt/anaconda3/bin/uvicorn src.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "  Backend starting at http://localhost:8000"

# Start frontend
cd "$PROJECT/frontend"
/opt/homebrew/bin/npm run dev &
FRONTEND_PID=$!
echo "  Frontend starting at http://localhost:5173"

echo ""
echo "  Opening browser in 3 seconds..."
sleep 3
open http://localhost:5173

echo ""
echo "  Both servers running. Press Ctrl+C to stop."
echo ""

# Stop both on Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'; exit" INT
wait
