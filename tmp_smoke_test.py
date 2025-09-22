import threading, time, requests
from agent_setup import vm_agent

def start_server():
    try:
        vm_agent.run_server(port=8010, host='127.0.0.1', dry_run=True)
    except Exception as e:
        print('server error', e)

thread = threading.Thread(target=start_server, daemon=True)
thread.start()

# wait for server to start
for i in range(10):
    try:
        r = requests.get('http://127.0.0.1:8010/status', timeout=1)
        print('status', r.status_code, r.text)
        break
    except Exception as e:
        print('waiting...', i, e)
        time.sleep(0.5)
else:
    print('failed to contact server')

# allow server to run a short while then exit
time.sleep(0.5)
