# Riko Remote Control

A remote desktop control and monitoring system with real-time video streaming and automatic updates.

## Features

- **Remote Screenshot Capture**: Get real-time screenshots from remote machines
- **Live Video Streaming**: MJPEG streaming for real-time desktop viewing
- **Action Execution**: Execute mouse clicks, keyboard input, and scrolling remotely
- **Automatic Updates**: Self-updating agent that pulls latest code from repository
- **Force Update**: Manual update trigger via HTTP endpoint
- **Security**: Token-based authentication and audit logging

## Quick Start

### Remote Machine Setup
1. Copy the `remote_setup/` folder to your remote Windows machine
2. Run `install_remote.bat` (installs Python, Git, and dependencies)
3. The agent starts automatically on port 8000

### Host Machine Connection
```bash
# Set environment variable for remote IP
$env:VM_AGENT_URL = 'http://REMOTE_IP:8000'

# Start the viewer
python vm_stream_viewer.py
```

## API Endpoints

- `GET /status` - System status and information
- `GET /screenshot` - Base64 encoded JPEG screenshot
- `GET /stream` - MJPEG video stream (~10 FPS)
- `POST /exec` - Execute actions (requires authentication)
- `POST /update` - Force immediate update check

## Security

- Agent runs in **live-run mode** by default (executes actions)
- Use `--dry-run` flag for safe logging-only mode
- Set `REMOTE_API_TOKEN` environment variable for authentication
- All actions are logged with timestamps and IP addresses

## Auto-Update

The remote agent automatically checks for updates every 5 minutes and updates itself. You can also force an update:

```bash
# From host machine
Invoke-WebRequest -Uri "http://REMOTE_IP:8000/update" -Method POST
```

## Requirements

- **Remote Machine**: Windows with internet access
- **Host Machine**: Python 3.x with OpenCV
- **Network**: Remote machine must be accessible from host

## Installation

1. Clone this repository
2. Copy `remote_setup/` to remote machine
3. Run `install_remote.bat` on remote machine
4. Connect from host using the stream viewer

## License

This project is for educational and personal use. Use responsibly and only on machines you have permission to control.