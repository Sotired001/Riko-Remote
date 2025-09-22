# Riko Agent

A desktop agent for monitoring and optional control of a machine with real-time video streaming and automatic updates.

## Features
# Riko Agent

A lightweight desktop agent for monitoring and (optionally) controlling a machine.

Features

- Real-time screenshot capture
- MJPEG streaming for live viewing
- Optional action execution (mouse/keyboard/scroll) — use only in trusted environments
- Automatic updates with an optional manual trigger
- Token-based authentication and audit logging

Quick start

1. Copy the `agent_setup/` folder to the machine you want to monitor.
2. (Optional) Set an environment variable: `AGENT_API_TOKEN` (if you need compatibility with older deployments, `REMOTE_API_TOKEN` is also accepted).
3. Run the installer or the agent script directly, for example:

```powershell
agent_setup\install_agent.bat
# or
python agent_setup\vm_agent.py
```

From the viewer machine:

```powershell
$env:VM_AGENT_URL = 'http://AGENT_IP:8000'
# Optional token
$env:AGENT_API_TOKEN = 'your-token'
python vm_stream_viewer.py
```

API endpoints

- GET /status — health and basic info
- GET /screenshot — base64-encoded JPEG (returns `no_change` when unchanged)
- GET /stream — MJPEG stream (~10 FPS)
- POST /exec — execute actions (requires token)
- POST /update — trigger an update check

Security

- Use `AGENT_API_TOKEN` for authenticated endpoints. `REMOTE_API_TOKEN` is supported for compatibility.
- Rate limiting defaults to 10 requests per minute per IP.
- Audit logs are written to `agent_audit.jsonl` (tokens are masked).

Auto-update

The agent periodically checks for updates and can be forced via `POST /update`.

License

This project is provided for educational and personal use. Use responsibly and only on systems you own or have permission to control.