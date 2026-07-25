# Jarvis OS v1 — User Guide

## Getting Started

### Prerequisites
- Python 3.10+
- Ollama (with qwen2.5-coder:7b model)
- Windows 10/11 (for system tray and auto-start)

### Installation
```bash
# Clone the repository
git clone https://github.com/varunkumar06011/My-jarvis.git
cd jarvis

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Ollama
ollama pull qwen2.5-coder:7b
ollama serve
```

### Running Jarvis

#### Production Mode (GUI + Tray + API)
```bash
python app/bootstrap.py
```
This starts:
- Native PySide6 desktop window
- System tray icon
- Wake word detection
- Secure API server at http://localhost:8100
- Web client at http://localhost:8100/web

#### Development Mode (CLI)
```bash
python main.py
```

## Using the GUI

### Home Dashboard
Shows real-time system status: lifecycle state, CPU, memory, plugins, uptime.

### Chat
Type messages to Jarvis. Responses come from the local LLM (Ollama).
Tool queries (time, date, calculator, battery) are routed automatically.

### Automation
Create and monitor automated workflows. Approve high-risk operations.

### AI CTO
View project health, security risks, performance regressions.
Generate daily/weekly/monthly reports.
Run architecture analysis to identify bottlenecks and hotspots.

### Learning
- **Patterns**: Reusable solutions tracked by success rate
- **Decisions**: Architecture decision records
- **Preferences**: Your coding style, naming conventions, frequent workflows

### Marketplace
Discover, install, update, and manage plugins.

### Settings
- Toggle wake word
- Adjust voice sensitivity
- Enable Windows auto-start
- Change Whisper model

## Voice Commands
1. Say "Hey Jarvis" to activate
2. Speak your request
3. Say "goodbye" to end conversation

## API Access
- Base URL: `http://localhost:8100`
- API Key: Set `JARVIS_API_DEFAULT_KEY` in `.env`
- Docs: `http://localhost:8100/docs`
- WebSocket: `ws://localhost:8100/ws`

## Web Client
Open `http://localhost:8100/web` in any browser for a chat interface.

## Troubleshooting

### Ollama out of memory
- Jarvis uses CPU-only inference by default (`GPU_LAYERS = 0`)
- Stale `llama-server.exe` processes are automatically cleaned up
- If issues persist, run: `taskkill /F /IM llama-server.exe`

### Wake word not detected
- Ensure microphone is working
- Lower `WAKE_THRESHOLD` in `configs/config.py` (try 0.2)
- Check ambient noise level

### Port 8100 already in use
- Jarvis automatically kills stale processes on startup
- Manually: `Get-NetTCPConnection -LocalPort 8100 | Stop-Process -Force`
