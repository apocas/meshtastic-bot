"""
Node Reboot Action

This action reboots the Meshtastic node every 6 hours for maintenance.
"""

import time
import os

# Configuration
INTERVAL_SECONDS = int(os.getenv("REBOOT_INTERVAL_SECONDS", "21600"))  # 6 hours default

# Action state
last_run_time = 0


def should_run():
    """Check if this action should run based on its interval."""
    global last_run_time
    current_time = time.time()
    
    # Don't run on first boot - initialize the timer
    if last_run_time == 0:
        last_run_time = current_time
        return False
    
    if current_time - last_run_time >= INTERVAL_SECONDS:
        return True
    return False


def execute(interface, my_node_num):
    """Execute the node reboot action."""
    global last_run_time
    
    try:
        print("\n[🔄] Initiating node reboot (6-hour maintenance)...")
        
        # Use the proper reboot method from the interface
        interface.localNode.reboot()
        
        print("[✅] Reboot command sent successfully")
        print("[💡] Note: Device will restart and may temporarily disconnect.\n")
        
        # Update last run time
        last_run_time = time.time()
        
        # Give some time for the command to be processed
        time.sleep(5)
        
    except Exception as e:
        print(f"[❌] Failed to reboot node: {e}")
        # Still update the time to prevent spam attempts
        last_run_time = time.time()


def get_info():
    """Return information about this action."""
    return {
        "name": "Node Rebooter",
        "description": "Reboots the Meshtastic node for maintenance",
        "interval_minutes": INTERVAL_SECONDS // 60,
        "last_run": last_run_time
    }
