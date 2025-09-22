# Migration TODO - remote → agent

This file documents the migration from "remote" naming to "agent" naming and contains a checklist, notes, commands for verification, and a rollback plan.

## Summary
We migrated code and docs from `remote` → `agent` naming. Canonical runtime code now lives under `agent_setup/`. Legacy locations were backed up and/or replaced with deprecation stubs.

## Checklist
- [x] Scan repository for `remote` occurrences and build a plan
- [x] Create canonical files under `agent_setup/` (host_agent.py, vm_agent.py, install_agent.bat)
- [x] Update main `README.md` to use agent naming
- [x] Migrate or stub legacy `remote_setup/` files
- [x] Update auto-update repository URLs to `https://github.com/Sotired001/riko-agent.git`
- [ ] Run runtime smoke tests (start agent + viewer)
- [ ] Commit changes and open PR with migration notes
- [ ] Notify downstream users and update any deployment scripts that reference old repo names

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

If you'd like, I can run the smoke tests and/or create a commit and open a pull request with a migration summary. Which would you like next?