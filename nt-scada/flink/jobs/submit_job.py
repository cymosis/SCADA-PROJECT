#!/usr/bin/env python3
import subprocess
import time
import requests
import os

FLINK_REST_URL = os.getenv("FLINK_REST_URL", "http://flink-jobmanager:8081")
JOB_FILE = "/opt/flink/jobs/realtime_analytics.py"

def wait_for_flink():
    for i in range(10, 0, -1):
        try:
            r = requests.get(f"{FLINK_REST_URL}/overview")
            if r.status_code == 200:
                print("✓ Flink cluster is running")
                return True
        except:
            print(f"Waiting for Flink cluster... {i}")
            time.sleep(5)
    return False

def submit_job():
    cmd = ["flink", "run", "--detached", "--jobmanager", "flink-jobmanager:8081", "--python", JOB_FILE]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    if result.returncode == 0:
        print("✓ Job submitted successfully")
    else:
        print(" Job submission failed")

if __name__ == "__main__":
    if wait_for_flink():
        submit_job()
