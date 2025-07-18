#!/usr/bin/env python3
"""
Standalone worker script for processing jobs in production.
Run separately from the web application.

Usage:
    python worker.py --workers 2 --redis-url redis://localhost:6379/0
"""

import argparse
import os
import sys
import signal
import time
from job_processor import JobManager

def main():
    parser = argparse.ArgumentParser(description='Job processing worker')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes')
    parser.add_argument('--redis-url', default='redis://localhost:6379/0', help='Redis URL')
    parser.add_argument('--max-concurrent', type=int, default=1, help='Max concurrent jobs per worker')
    
    args = parser.parse_args()
    
    print(f"Starting job worker with {args.workers} processes")
    print(f"Redis URL: {args.redis_url}")
    print(f"Max concurrent jobs per worker: {args.max_concurrent}")
    
    # Create job manager
    job_manager = JobManager(args.redis_url, args.workers)
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print(f"\nReceived shutdown signal ({signum})")
        job_manager.stop_workers()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start workers
        job_manager.start_workers()
        
        # Keep main process alive and show stats
        while True:
            try:
                stats = job_manager.get_queue_stats()
                print(f"Queue Stats - Pending: {stats['pending']}, Processing: {stats['processing']}, Total: {stats['total']}")
                time.sleep(30)  # Show stats every 30 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error getting stats: {e}")
                time.sleep(5)
    
    except Exception as e:
        print(f"Worker error: {e}")
        job_manager.stop_workers()
        sys.exit(1)
    
    finally:
        job_manager.stop_workers()

if __name__ == '__main__':
    main()
