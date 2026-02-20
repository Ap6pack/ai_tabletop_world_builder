Start the AI Tabletop World Builder development environment.

## Instructions

0. **Activate the shared virtual environment** before running any Python commands:
   ```
   source /home/localhost/Projects/shared_venv/bin/activate
   ```

1. **Check prerequisites**:
   - Python 3.11+ is installed
   - Required dependencies are installed (check `requirements.txt`)
   - `.env` file exists (if not, warn the user)

2. **Start the backend API**:
   ```
   python main.py
   ```
   - Runs on http://localhost:8000
   - API docs at http://localhost:8000/docs
   - Run in background

3. **Wait for backend health check**:
   - Hit http://localhost:8000/health
   - Wait up to 10 seconds for it to become available

4. **Start the Streamlit frontend**:
   ```
   cd app && streamlit run Home.py --server.port 8501
   ```
   - Runs on http://localhost:8501
   - Run in background

5. **Report status**:
   - Backend: Running on :8000 / Failed to start
   - Frontend: Running on :8501 / Failed to start
   - Log locations: `logs/api.log`, `logs/streamlit.log`

6. **Note**: Both processes run in the background. Use `pkill -f "python main.py"` and `pkill -f "streamlit"` to stop them.
