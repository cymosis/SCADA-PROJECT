#!/usr/bin/env python3
"""
Simple Flink Job Submission for Real-time Analytics
"""

import subprocess
import sys
import time
import requests

# Flink cluster configuration
FLINK_REST_URL = "http://flink-jobmanager:8081"
JOB_FILE = "/opt/flink/jobs/realtime_analytics.py"

def check_flink_cluster():
    """Check if Flink cluster is running"""
    retries = 10
    while retries > 0:
        try:
            response = requests.get(f"{FLINK_REST_URL}/overview", timeout=5)
            if response.status_code == 200:
                print("✓ Flink cluster is running")
                return True
            else:
                print(f"Flink cluster responded with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Waiting for Flink cluster... ({retries} retries left)")
            retries -= 1
            time.sleep(5)
    
    print("✗ Cannot connect to Flink cluster after multiple attempts")
    return False

def submit_analytics_job():
    """Submit the real-time analytics job"""
    try:
        cmd = [
            "flink", "run",
            "--detached", 
            "--jobmanager", "flink-jobmanager:8081",
            "--python", JOB_FILE
        ]
        
        print(f"Submitting analytics job: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Real-time analytics job submitted successfully")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"✗ Job submission failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error submitting job: {e}")
        return False

def get_running_jobs():
    """Get list of currently running jobs"""
    try:
        response = requests.get(f"{FLINK_REST_URL}/jobs", timeout=5)
        if response.status_code == 200:
            jobs = response.json().get('jobs', [])
            running_jobs = [job for job in jobs if job['status'] in ['RUNNING', 'RESTARTING']]
            print(f"Found {len(running_jobs)} running jobs")
            return running_jobs
        else:
            print(f"Failed to get jobs: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting jobs: {e}")
        return []

def is_analytics_job_running(jobs):
    """Check if our analytics job is already running"""
    for job in jobs:
        if 'analytics' in job['name'].lower() or 'realtime' in job['name'].lower():
            print(f"Analytics job found: {job['name']} (ID: {job['id']}, Status: {job['status']})")
            return True
    return False

def main():
    """Main continuous job manager loop"""
    print("Flink Job Manager - Continuous Monitoring")
    print("=" * 50)
    
    CHECK_INTERVAL = 30  # Check every 30 seconds
    
    while True:
        try:
            # Check if Flink cluster is running
            if not check_flink_cluster():
                print("Flink cluster not available, waiting...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Get current running jobs
            running_jobs = get_running_jobs()
            
            # Check if analytics job is running
            if not is_analytics_job_running(running_jobs):
                print("Analytics job not found, submitting...")
                if submit_analytics_job():
                    print("🎯 Analytics job submitted successfully!")
                    print("📊 View at: http://localhost:8081")
                else:
                    print("❌ Failed to submit analytics job")
            else:
                print("✓ Analytics job is running")
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("Job manager stopped by user")
            break
        except Exception as e:
            print(f"Unexpected error in job manager: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
