# Riko Agent Development TODO & Status

next steps for Both orchestrator and agent-side development. 

## Notes You must take detailed notes for argent as you will not be working on it ##

## Orchestrator Development Status

## Project Migration Status (COMPLETED)
We successfully migrated from `remote` → `agent` naming. Canonical runtime code lives under `agent_setup/`.

### Migration Checklist ✅
- [x] Scan repository for `remote` occurrences and build a plan
- [x] Create canonical files under `agent_setup/` (host_agent.py, vm_agent.py, install_agent.bat)
- [x] Update main `README.md` to use agent naming
- [x] Migrate or stub legacy `remote_setup/` files
- [x] Update auto-update repository URLs to `https://github.com/Sotired001/riko-agent.git`
- [x] Run runtime smoke tests (agent responds to /status)
- [x] Commit changes and open PR with migration notes
- [ ] Notify downstream users and update any deployment scripts that reference old repo names

## Web Orchestrator Development Status

### Phase 1: Core Infrastructure ✅ COMPLETED
- [x] **Multi-Agent Management**: Dashboard showing multiple agents simultaneously
- [x] **Web UI Architecture**: Replace OpenCV viewer with Flask + SocketIO web interface
- [x] **Local AI Assistant**: Natural language command interface using Ollama
- [x] **Multi-Monitor Support**: Agent endpoints for multiple screens, UI tabs for screen switching
- [x] **Real-time Updates**: SocketIO for live agent status and screenshot updates
- [x] **Basic Agent Management**: Add/remove agents, manual refresh, status monitoring

### Phase 2: Discovery & UI Polish ✅ COMPLETED
- [x] **Agent Discovery Implementation**: Local port scanning (8000-8003) with server-side discovery
- [x] **Discovery UI Wiring**: Frontend handlers for discovery results, add discovered agents
- [x] **Refresh API**: Individual agent refresh endpoint (`POST /api/agents/<id>/refresh`)
- [x] **Rate Limiting Fixes**: Increased agent rate limits (10→60 req/min), slower orchestrator polling
- [x] **JSON Serialization**: Fixed SocketIO emissions (exclude non-serializable client objects)
- [x] **Multi-Screen UI**: Screen tabs, screen switching, coordinated screenshot fetching

### Phase 3: Current Development Status 🚧 IN PROGRESS

#### Recently Completed (Dec 2024):
1. **Frontend Discovery Integration** ✅
   - Added Socket.IO handler for `discovery_result` events
   - Discovery results panel with agent list and "Add" buttons
   - `addDiscoveredAgent(url)` function for one-click agent addition

2. **Agent Refresh Implementation** ✅
   - `refreshAgent(agentId)` calls `POST /api/agents/<id>/refresh`
   - Server emits `agent_update` after refresh (UI auto-updates)
   - Error handling for failed refresh attempts

3. **Basic Agent Details** ✅
   - `openAgentDetails(agentId)` fetches `/api/agents/<id>/screens`
   - Shows agent metadata and screen information in alert dialog
   - Provides screen resolution, position, and primary screen indicators

#### Current Issues & Blockers:

**1. Port Conflicts** 🚨 CRITICAL
- `OSError: [WinError 10048]` - Port 5000 already in use
- Root cause: Flask development server + SocketIO eventlet conflict
- Multiple Python processes not properly terminating
- Solutions to implement:
  - Add port detection loop (try 5000, 5001, 5002, etc.)
  - Implement graceful shutdown handler
  - Add process cleanup on startup
  - Consider using different WSGI server (gunicorn, waitress)

**2. Screenshot Delivery** ⚠️ HIGH PRIORITY
- Screenshots intermittently not appearing in UI
- Potential causes identified:
  - Agent rate limiting (429 responses) - partially fixed by increasing limits
  - Base64 encoding/decoding chain issues
  - PIL Image handling in get_screenshot_from_screen()
  - Network timing issues between orchestrator and agents
  - SocketIO emission timing (agent_update before screenshot ready)
- Debugging steps:
  - Check browser network tab for failed /screenshot requests
  - Monitor agent logs for rate limit messages
  - Verify base64 data in agent_update SocketIO messages
  - Test direct agent /screenshot/0 endpoint with curl

**3. Modal UI** 📋 MEDIUM PRIORITY
- Agent details currently use browser alert() dialogs
- Needed: proper modal implementation for:
  - Agent details with full screen information
  - Full-size screenshot viewing
  - Discovery results (replace alert notifications)
  - Error messages and confirmations
- Modal should include:
  - Agent metadata (name, URL, status, uptime)
  - Screen information table with resolution/position
  - Performance metrics (response time, last seen)
  - Full-size screenshot with zoom/pan capabilities
  - Action buttons (refresh, remove, test actions)

**4. Error Handling** 📋 MEDIUM PRIORITY
- Inconsistent error handling across frontend
- No proper error states for:
  - Failed agent connections
  - Screenshot loading failures
  - Discovery timeouts
  - AI assistant unavailable
- Need standardized error UI patterns

**5. Rate Limiting & Performance** ⚠️ ONGOING
- Agent rate limits increased (10→60 req/min) but may need further tuning
- Orchestrator polling every 5 seconds may be too aggressive for many agents
- Screenshot caching not implemented (re-fetches same screenshot repeatedly)
- Need client-side exponential backoff for 429 responses

#### Architecture Notes:
```
orchestrator_web.py (Flask + SocketIO)
├── AgentManager class
│   ├── Background monitoring thread (polls agents every 5s)
│   ├── Agent registry with AgentAgentClient instances
│   ├── JSON serialization for SocketIO emissions
│   ├── update_agent_status() - polls /status, /screens, /screenshot/0
│   ├── get_agents() - returns JSON-safe agent data (excludes client objects)
│   └── _monitor_loop() - background thread, emits agent_update via SocketIO
├── API endpoints
│   ├── /api/agents (GET/POST/DELETE) - agent CRUD operations
│   ├── /api/agents/<id>/exec - action execution (requires raw agents dict)
│   ├── /api/agents/<id>/refresh - force update + emit agent_update
│   ├── /api/agents/<id>/screenshot[/<screen_id>] - base64 image response
│   ├── /api/agents/<id>/screens - screen metadata from agent
│   └── /api/ai/* - AI assistant integration (LocalAI/Ollama)
├── SocketIO handlers
│   ├── connect(auth) - emit agent_update on client connect
│   └── discover_agents() - localhost port scan (8000-8003), emit discovery_result
└── Global state management
    ├── agent_manager (AgentManager instance)
    ├── agent_lock (threading.Lock for thread safety)
    └── ai_assistant (AIAssistant instance, lazy-loaded)

templates/orchestrator.html (Frontend)
├── Socket.IO client integration
│   ├── agent_update handler - updates global agents dict, calls updateUI()
│   ├── discovery_result handler - populates discovery list, shows alert
│   └── connect handler - calls checkAIStatus()
├── Agent grid with multi-view support
│   ├── updateAgentGrid() - renders agent cards with screenshots
│   ├── generateScreenshotContent() - handles multi-screen UI
│   ├── switchScreen() - fetches /screenshot/<id> for specific screens
│   └── View modes: grid, large, compact, list, fullscreen
├── Discovery panel with results list
│   ├── discoverAgents() - emits 'discover_agents' to server
│   ├── addDiscoveredAgent() - POST to /api/agents with discovered URL
│   └── Discovery results UI in #discovery-list container
├── Agent management functions
│   ├── addAgent() - manual agent addition form
│   ├── removeAgent() - DELETE /api/agents/<id>
│   ├── refreshAgent() - POST /api/agents/<id>/refresh
│   ├── openAgentDetails() - fetch /screens and show alert (TODO: modal)
│   └── executeAction() - POST /api/agents/<id>/exec for testing
├── AI chat interface
│   ├── sendAICommand() - POST /api/ai/command
│   ├── checkAIStatus() - GET /api/ai/status
│   └── addChatMessage() - UI message management
└── Multi-screen tabs and switching
    ├── Screen tab UI generation in generateScreenshotContent()
    ├── switchScreen() - dynamic screenshot loading per screen
    └── showScreenDetails() - screen metadata display (TODO: modal)
```

#### Critical Implementation Details:

**AgentManager Thread Safety:**
- Uses `agent_lock` for thread-safe access to agents dict
- Background monitoring thread updates agent status every 5 seconds
- get_agents() excludes non-serializable AgentAgentClient objects
- Raw agents dict used in exec endpoint to access client objects

**SocketIO Event Flow:**
1. Client connects → server emits agent_update with current agents
2. Discovery: client emits 'discover_agents' → server scans ports → emits 'discovery_result'
3. Add agent: POST /api/agents → server calls update_agent_status() → emits agent_update
4. Refresh: POST /api/agents/<id>/refresh → server updates status → emits agent_update
5. Monitor loop: continuous agent polling → periodic agent_update emissions

**Screenshot Handling Chain:**
1. AgentManager.update_agent_status() calls client.get_screenshot_from_screen(0)
2. AgentAgentClient.get_screenshot_from_screen() calls agent /screenshot/<id>
3. Agent returns base64 JPEG in JSON response
4. Client decodes base64 → PIL Image → re-encodes as base64 for storage
5. Frontend receives base64 via agent_update → displays as data: URL

**Multi-Screen UI Flow:**
1. Agent /status returns screens array from _get_screen_info()
2. Frontend generateScreenshotContent() creates tabs for multiple screens
3. switchScreen() fetches /api/agents/<id>/screenshot/<screen_id>
4. Server calls agent_manager.get_agent_screenshot() → client.get_screenshot_from_screen()
5. Response updates screen-display-<agentId> container with new image

## Next Priority Tasks

### Immediate (This Session):
1. **Fix Port Conflicts** 🚨
   - Implement port detection loop in orchestrator_web.py
   - Add graceful shutdown handlers for Flask + SocketIO
   - Consider switching to different WSGI server (waitress/gunicorn)
   - Test process cleanup: ensure `taskkill /f /im python.exe` clears all processes

2. **Test End-to-End Flow** 🧪
   - Start orchestrator on available port (5000-5010 range)
   - Start local agent: `python agent_setup/vm_agent.py --port 8001`
   - Test discovery workflow: click "Discover Agents" → verify agent found
   - Test add agent: click "Add" on discovered agent → verify appears in grid
   - Test screenshots: verify agent card shows screenshot image
   - Test refresh: click "Refresh" on agent → verify immediate update
   - Test details: click "Details" → verify screen information displayed

### Short Term (Next Week):
3. **Implement Modal UI** 📋
   - Create modal component in templates/orchestrator.html
   - Replace alert() dialogs with proper modals:
     - Agent details modal with full screen information
     - Full-size screenshot viewer with zoom functionality
     - Discovery results modal (replace alert notifications)
     - Error message modal for failed operations
   - Modal features:
     - Agent metadata table (name, URL, status, uptime, response time)
     - Screen information grid with resolution/position/primary indicators
     - Action buttons (refresh, remove, test click/type actions)
     - Full-size screenshot with click-to-zoom functionality
     - Performance charts (response time history, connection quality)

4. **Screenshot Retry Logic** 🔄
   - Implement exponential backoff for 429 responses in switchScreen()
   - Add loading states during screenshot fetch operations
   - Show error states for failed screenshot requests
   - Implement client-side screenshot caching with timestamps
   - Add retry button for failed screenshot loads
   - Show placeholder images during loading/error states

### Medium Term (Next Month):
5. **Enhanced Discovery** 🌐
   - Replace localhost port scanning with mDNS/Bonjour discovery
   - Add configurable IP ranges for discovery (192.168.1.1-254)
   - Implement agent auto-registration via UDP broadcast
   - Add manual IP/hostname entry for remote agents
   - Support discovery profiles (home network, office network, etc.)

6. **Performance & Monitoring** 📊
   - Implement agent health monitoring with alerts
   - Add performance metrics dashboard (response times, uptime, errors)
   - Historical data storage and trending charts
   - Agent resource monitoring (CPU, memory, disk usage)
   - Network latency and bandwidth monitoring
   - Automated alerts for disconnected/slow agents

7. **Production Readiness** 🚀
   - Replace Flask development server with production WSGI server
   - Add configuration file support (YAML/JSON config)
   - Implement proper logging with log levels and rotation
   - Add authentication/authorization for orchestrator access
   - SSL/TLS support for secure communication
   - Database backend for persistent agent configurations
   - Docker containerization with docker-compose setup
   - Automated backup and recovery procedures

### Long Term (Next Quarter):
8. **Advanced Features** ⭐
   - Agent clustering and load balancing
   - Distributed orchestrator with multiple instances
   - Plugin system for custom agent actions
   - Workflow automation and scheduling
   - Integration with external monitoring systems (Prometheus, Grafana)
   - Mobile app for orchestrator management
   - REST API documentation with OpenAPI/Swagger
   - Automated testing suite with CI/CD pipeline

## Agent-Side Development TODO

### Current Agent Capabilities ✅
- **Multi-Monitor Support**: `/screens` endpoint, `/screenshot/<id>` for specific screens
- **Rate Limiting**: 60 requests/minute per IP (increased from 10)
- **Enhanced Actions**: Multi-screen click/type/scroll with relative coordinates
- **Auto-Updates**: Git-based auto-update with 5-minute intervals
- **Security**: Token-based authentication, audit logging

### Planned Agent Enhancements:
- [ ] **Enhanced Security**
  - [ ] Certificate-based authentication
  - [ ] Role-based access control (RBAC)
  - [ ] Secure communication channels (TLS/SSL)
  - [ ] Enhanced audit logging with tamper protection

- [ ] **Performance & Monitoring**
  - [ ] Real-time performance metrics collection
  - [ ] Resource usage monitoring (CPU, RAM, Disk)
  - [ ] Predictive performance analytics
  - [ ] Bottleneck detection and optimization recommendations

- [ ] **Management & Operations**
  - [ ] Configuration templates and bulk updates
  - [ ] Deployment pipelines and automation
  - [ ] Backup and recovery mechanisms
  - [ ] Version management and rollback capabilities

- [ ] **Advanced Features**
  - [ ] Plugin/extension system
  - [ ] Agent clustering and coordination
  - [ ] Auto-scaling capabilities
  - [ ] Network resilience and failover

## Technical Debt & Known Issues

### Fixed Issues ✅:
- **JSON Serialization**: AgentAgentClient objects excluded from SocketIO emissions
- **Socket Handler Signatures**: Fixed connect handler to accept auth parameter
- **Rate Limiting**: Coordinated agent limits with orchestrator polling frequency
- **KeyError Issues**: Used raw agent dict for endpoints requiring client access

### Current Technical Debt:
1. **Error Handling**: Inconsistent error handling across API endpoints
2. **Logging**: Limited structured logging for debugging
3. **Configuration**: Hard-coded values (ports, timeouts, polling intervals)
4. **Testing**: No automated test suite for orchestrator or agents
5. **Documentation**: API documentation incomplete

### Performance Considerations:
- **Memory Usage**: Screenshot caching strategy needs optimization
- **Network Bandwidth**: Large screenshot transfers could impact performance
- **Concurrent Agents**: Scalability testing needed for 10+ agents
- **Database**: Consider persistent storage for agent configurations and history

## Development Environment Notes

### Dependencies:
```
orchestrator_web.py requirements:
- flask>=2.3.0
- flask-socketio>=5.3.0
- requests>=2.31.0
- pillow>=10.0.0

AI Assistant (optional):
- Ollama (external binary)
- Local AI model: llama3.2

Agent requirements:
- pillow (required)
- pyautogui (optional, for actions)
```

### Testing Commands:
```powershell
# Start orchestrator
python orchestrator_web.py

# Start test agent
python agent_setup/vm_agent.py --port 8001

# Check agent status
curl http://localhost:8001/status

# Test discovery
# Open http://localhost:5000, click "Discover Agents"
```

### Debugging Tips:
1. **Port Conflicts**: 
   - Use `netstat -ano | findstr ":5000"` to find conflicting processes
   - Kill processes with `taskkill /f /pid <PID>`
   - Try alternative ports: modify `socketio.run(app, port=5001)` in orchestrator_web.py

2. **Agent Communication**: 
   - Check agent logs for 429 rate limit errors
   - Test direct agent endpoints: `curl http://localhost:8001/status`
   - Verify agent /screenshot/0 returns base64 data
   - Monitor agent_audit.jsonl for action logs

3. **SocketIO Issues**: 
   - Monitor browser console for connection errors
   - Check Network tab for failed WebSocket connections
   - Verify agent_update events contain expected data structure
   - Test SocketIO manually: `socket.emit('discover_agents')` in browser console

4. **Screenshot Problems**: 
   - Verify base64 encoding: check if agent_update contains 'screenshot' field
   - Test PIL image handling: ensure get_screenshot_from_screen() returns valid Image
   - Check browser data URLs: inspect img src attributes in DevTools
   - Monitor for truncated base64 data (memory/size limits)

5. **AI Assistant Issues**:
   - Verify Ollama running: `ollama serve` in separate terminal
   - Check model availability: `ollama list | findstr llama3.2`
   - Test AI endpoint directly: `curl http://localhost:5000/api/ai/status`
   - Monitor AI chat logs in browser console

### Common Error Patterns & Solutions:

**"AgentAgentClient is not JSON serializable"**
- Cause: Trying to emit client objects via SocketIO
- Solution: Use agent_manager.get_agents() which excludes client objects
- Location: Any SocketIO emit() call with agent data

**"KeyError: 'client'"**  
- Cause: Using serialized agents dict where raw agents dict needed
- Solution: Use agent_manager.agents directly for client access
- Location: /api/agents/<id>/exec endpoint

**"429 Too Many Requests"**
- Cause: Agent rate limiting (60 req/min per IP)
- Solution: Increase agent rate limits or slow orchestrator polling
- Location: AgentManager._monitor_loop() and agent_setup/vm_agent.py

**Empty/Missing Screenshots**
- Cause: Agent screenshot capture failing or base64 encoding issues
- Solution: Check agent logs, verify PIL ImageGrab.grab() works
- Debug: Test agent /screenshot endpoint directly

**Discovery Returns No Results**
- Cause: No agents running on localhost:8000-8003
- Solution: Start test agent with `python agent_setup/vm_agent.py --port 8001`
- Debug: Check if ports respond to HTTP requests

### Performance Optimization Notes:

**Screenshot Caching Strategy:**
- Current: No caching, re-fetches same screenshot repeatedly
- Proposed: Client-side cache with timestamp checking
- Implementation: Store screenshots with last-modified headers
- Benefits: Reduce network traffic, improve UI responsiveness

**Agent Polling Optimization:**
- Current: Poll all agents every 5 seconds regardless of activity
- Proposed: Adaptive polling based on agent responsiveness
- Implementation: Increase intervals for slow/error agents
- Benefits: Reduce network load, improve scalability

**Memory Management:**
- Current: Screenshots stored as base64 strings in memory
- Issue: Large screenshots (4K displays) consume significant memory
- Solutions: Implement image compression, thumbnail generation
- Consider: Streaming screenshots instead of full image transfer

## Instructions for Future Development

**Critical Orchestrator Development Guidelines:**

**Before Making Changes:**
- Always backup the current working version
- Test changes with multiple agents (minimum 2, preferably 3+)
- Verify SocketIO emissions are JSON-serializable (no client objects)
- Check for port conflicts before starting development sessions

**Frontend Development (templates/orchestrator.html):**
- Socket.IO event handlers must handle connection failures gracefully
- All fetch() calls should include error handling and loading states
- Screenshot data URLs must be validated before setting img.src
- Modal implementations should use semantic HTML and proper ARIA labels
- Multi-screen functionality requires careful state management per agent
- Always test UI responsiveness across different screen sizes

**Backend Development (orchestrator_web.py):**
- AgentManager thread safety: always use agent_lock for shared state
- SocketIO emissions: use get_agents() not raw agents dict
- API endpoints requiring client access: use raw agent_manager.agents
- Background monitoring: be mindful of polling frequency vs. agent rate limits
- Error handling: return consistent JSON error responses with HTTP status codes
- Agent client instantiation: handle network timeouts and connection failures

**Testing Protocol:**
1. Start orchestrator on clean port (kill existing processes first)
2. Start 2+ agents on different ports (8001, 8002)
3. Test discovery workflow end-to-end
4. Verify agent cards show screenshots within 10 seconds
5. Test multi-screen switching if agents have multiple displays
6. Test all modal dialogs and error states
7. Monitor browser console for JavaScript errors
8. Check agent logs for rate limiting or connection issues

**Common Pitfalls to Avoid:**
- Never emit AgentAgentClient objects via SocketIO (causes serialization errors)
- Don't use serialized agents dict in endpoints that need client access
- Avoid hardcoded timeouts - make them configurable
- Don't ignore rate limiting - coordinate polling with agent limits
- Never assume agents are always available - handle timeouts gracefully
- Don't block the UI thread with synchronous operations

**Code Organization Principles:**
- Keep AgentManager focused on agent lifecycle and monitoring
- Separate API logic from SocketIO event handling
- Use consistent error response formats across all endpoints
- Implement proper logging at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Keep frontend state management simple and predictable
- Use semantic CSS classes and avoid inline styles

**Performance Considerations:**
- Screenshot caching strategy must balance memory usage vs. network requests
- Agent polling frequency should adapt based on agent responsiveness
- Large screenshots (4K displays) may need compression or thumbnails
- Consider implementing pagination for many agents (10+ agents)
- Monitor memory usage during long-running sessions
- Implement connection pooling for agent HTTP requests

**Security Considerations:**
- Validate all user inputs before sending to agents
- Sanitize agent responses before displaying in UI
- Implement proper authentication for orchestrator access in production
- Use HTTPS for all communications in production environments
- Validate agent URLs to prevent SSRF attacks
- Implement rate limiting on orchestrator API endpoints

**When working on agent features:**
- Ensure backwards compatibility with existing orchestrator
- Test multi-monitor functionality on systems with multiple displays
- Verify rate limiting doesn't break legitimate usage
- Document API changes and version requirements

**Before major releases:**
- Run full end-to-end test with orchestrator + multiple agents
- Test AI assistant integration (if Ollama available)
- Verify all screenshots load and refresh correctly
- Test discovery on different network configurations
- Performance test with 5+ agents running simultaneously
- Test graceful degradation when agents become unavailable
- Verify proper cleanup of resources on shutdown

## Verification commands (run locally in PowerShell)
# Run quick syntax checks on modified Python files
python -m py_compile agent_setup\host_agent.py agent_setup\vm_agent.py vm_stream_viewer.py

# Optionally run a small smoke test (dry-run agent + viewer)
# In one terminal: (starts agent in dry-run)
python agent_setup\vm_agent.py --dry-run

# In another terminal, point viewer at it and run
$env:VM_AGENT_URL = 'http://127.0.0.1:8000'
python vm_stream_viewer.py

## Rollback plan
1. If the migration causes issues, restore files from the backup folder `remote_setup.bak/`.
2. Revert changes via git (if you commit):
   - `git checkout -- .` will revert unstaged edits
   - `git reset --hard HEAD~1` will revert the last commit (use with care)
3. Revert auto-update repo_url changes by restoring the original repo URLs stored in the backup files.

## Notes
- Auto-update repo URL changes are a breaking migration for existing deployed agents that rely on the old repo; ensure downstream systems are updated or plan a migration window.
- If you prefer a smoother migration, re-introduce a temporary fallback to `REMOTE_API_TOKEN` in canonical agent code for a short period.

---