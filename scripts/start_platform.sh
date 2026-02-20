#!/bin/bash
# Quick start script for the Cybersecurity War Gaming Platform

echo "🚀 Starting Cybersecurity War Gaming Platform..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Please create .env with your API keys:"
    echo "  OPENAI_API_KEY=your-key-here"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Start backend API
echo "📡 Starting Backend API (port 8000)..."
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo "   API PID: $API_PID"

# Wait for API to be ready
echo "⏳ Waiting for API to start..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ API is ready!"
        break
    fi
    sleep 1
    if [ $i -eq 10 ]; then
        echo "❌ API failed to start. Check logs/api.log"
        kill $API_PID 2>/dev/null
        exit 1
    fi
done

echo ""

# Start Streamlit frontend
echo "🎨 Starting Streamlit Frontend (port 8501)..."
streamlit run app/Home.py > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "   Streamlit PID: $STREAMLIT_PID"

echo ""
echo "✅ Platform started successfully!"
echo ""
echo "📍 Access the application at:"
echo "   Frontend: http://localhost:8501"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Process IDs:"
echo "   API:       $API_PID"
echo "   Streamlit: $STREAMLIT_PID"
echo ""
echo "To stop the platform, run:"
echo "   kill $API_PID $STREAMLIT_PID"
echo ""
echo "Or save these to stop_platform.sh:"
echo "echo 'kill $API_PID $STREAMLIT_PID' > stop_platform.sh && chmod +x stop_platform.sh"
echo ""
echo "Logs available in:"
echo "   logs/api.log"
echo "   logs/streamlit.log"
