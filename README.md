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

### Host Machine Setup
1. Copy the `remote_setup/` folder to your Riko host machine
2. Run `install_remote.bat` (installs Python, Git, and dependencies)
3. The agent starts automatically on port 8000

### Remote Control Machine Connection
```bash
# Set environment variable for host IP
$env:HOST_AGENT_URL = 'http://HOST_IP:8000'

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

- **Authentication**: All sensitive endpoints require `REMOTE_API_TOKEN` environment variable
- **Rate Limiting**: Maximum 10 requests per minute per IP address
- **Network Binding**: Server binds to localhost (127.0.0.1) by default for security
- **Token Masking**: API tokens are masked in audit logs (only first 8 characters shown)
- **Audit Logging**: All actions are logged with timestamps, masked tokens, and client IPs
- **Error Handling**: Generic error messages prevent information leakage

**⚠️ Security Warning**: This system allows remote control of the host machine. Only run on trusted networks and ensure proper authentication is configured.

## Auto-Update

The host agent automatically checks for updates every 5 minutes and updates itself. You can also force an update:

```bash
# From remote control machine
Invoke-WebRequest -Uri "http://HOST_IP:8000/update" -Method POST
```

## Requirements

- **Host Machine**: Windows with internet access (runs Riko AI)
- **Remote Control Machine**: Python 3.x with OpenCV
- **Network**: Host machine must be accessible from remote control machine

## Installation

1. Clone this repository
2. Copy `remote_setup/` to host machine
3. Set environment variable: `$env:REMOTE_API_TOKEN = 'your-secure-token-here'`
4. Run `install_remote.bat` on host machine
5. Connect from remote control machine using the stream viewer

**Security Note**: Always set a strong, unique `REMOTE_API_TOKEN` before running the agent.

## License

This project is for educational and personal use. Use responsibly and only on machines you have permission to control.