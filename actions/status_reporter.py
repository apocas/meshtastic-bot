"""
Status Reporter Action

This action periodically reports the bot status and statistics.
"""

import time
import os

# Configuration
INTERVAL_SECONDS = int(os.getenv("STATUS_INTERVAL_SECONDS", "3600"))  # 1 hour default

# Action state
last_run_time = 0


def should_run():
    """Check if this action should run based on its interval."""
    global last_run_time
    current_time = time.time()
    
    if current_time - last_run_time >= INTERVAL_SECONDS:
        return True
    return False


def execute(interface, my_node_num):
    """Execute the status reporting action."""
    global last_run_time
    
    print("\n[📊] Bot Status Report:")
    
    # Get current nodes
    nodes = interface.nodes
    favorites_count = sum(1 for node in nodes.values() if node.get('isFavorite', False))
    mqtt_count = sum(1 for node in nodes.values() if node.get('viaMqtt', False))
    
    print(f"[📈] Node Statistics:")
    print(f"  - Total nodes in database: {len(nodes)}")
    print(f"  - Favorite nodes: {favorites_count}")
    print(f"  - MQTT nodes: {mqtt_count}")
    print(f"  - Direct RF nodes: {len(nodes) - mqtt_count}")
    
    # Device info
    try:
        print(f"[🔋] Device Info:")
        print(f"  - My Node ID: {my_node_num}")
        if hasattr(interface, 'myInfo') and interface.myInfo:
            print(f"  - Device connected: ✅")
        else:
            print(f"  - Device connected: ❌")
    except Exception as e:
        print(f"  - Error getting device info: {e}")
    
    print("[✅] Status report complete.\n")
    
    # Update last run time
    last_run_time = time.time()


def get_info():
    """Return information about this action."""
    return {
        "name": "Status Reporter",
        "description": "Reports bot and node statistics",
        "interval_minutes": INTERVAL_SECONDS // 60,
        "last_run": last_run_time
    }
