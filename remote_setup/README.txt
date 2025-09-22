Remote Agent Setup
==================

This folder contains everything needed to set up the remote agent on a Windows machine.

Files:
- vm_agent.py: The remote agent script.
- install_remote.bat: One-click installer that installs Python (if needed) and starts the agent.

Instructions:
1. Copy this entire folder to the remote Windows machine.
2. Double-click install_remote.bat to install and start the agent.
3. The agent will run on port 8000, providing /status, /screenshot, /stream, /exec, and /update endpoints.
   - It will print the URL, e.g., "VM agent running on http://0.0.0.0:8000 (local IP: <your-local-ip>)"
   - To find the remote machine's IP: Open Command Prompt on remote and run `ipconfig` (look for IPv4 Address under your network adapter).
4. The agent will automatically check for code updates every 5 minutes and restart if new code is available (requires Git).

For host-side viewing:
- On the host machine, set the environment variable: $env:VM_AGENT_URL = 'http://<remote-ip>:8000'
- Run the viewer: python scripts/vm_stream_viewer.py
- This will open a window showing the remote screen in real-time.
- Press 'q' to quit the viewer.

For actions:
- The host can send commands to the remote via /exec (executes actions in live-run mode by default).
- To force an immediate update check: POST to /update endpoint

Security:
- The agent runs in live-run mode (executes actions - use in isolated environments only).
- Use --dry-run to enable safe logging mode without execution.
- Optionally set REMOTE_API_TOKEN for authentication.

For deployment:
- Use the host's deploy_to_remote.ps1 to copy this folder automatically.
- Or set up automated deployment via GitHub Actions (see .github/workflows/deploy.yml):
  - Set repository secrets: REMOTE_HOST, REMOTE_PATH, SSH_KEY
  - Ensure SSH access to remote machine is configured
  - Push to the deployment branch to trigger automatic deployment