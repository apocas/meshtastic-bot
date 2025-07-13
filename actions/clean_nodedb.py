"""
Node Database Cleaner Action

This action cleans the node database by removing:
- MQTT nodes (viaMqtt: true)
- Nodes not heard from in the last 6 days
- Keeps favorites and own node
"""

import time
import os

# Configuration
INTERVAL_SECONDS = int(os.getenv("CLEAN_INTERVAL_SECONDS", "1800"))  # 30 minutes default
SIX_DAYS_SECONDS = 6 * 24 * 60 * 60  # 6 days

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
    """Execute the node database cleaning action."""
    global last_run_time
    
    print("\n[🧹] Starting automatic node database cleanup...")
    
    # Get current nodes
    nodes = interface.nodes
    current_time = int(time.time())
    print(f"[📊] Total nodes in database: {len(nodes)}")
    
    favorites_count = 0
    old_nodes_count = 0
    nodes_to_remove = []
    
    # Identify nodes to keep (favorites) and nodes to remove
    for node_id, node_data in nodes.items():
        is_favorite = node_data.get('isFavorite', False)
        last_heard = node_data.get('lastHeard', 0)
        is_own_node = node_data.get('num') == my_node_num
        via_mqtt = node_data.get('viaMqtt', False)
        
        # Calculate how long ago the node was last heard
        time_since_heard = current_time - last_heard if last_heard else float('inf')
        days_since_heard = time_since_heard / (24 * 60 * 60)
        
        node_name = node_data.get('user', {}).get('longName', 'Unknown')
        
        if is_own_node:
            print(f"[🏠] Own node (always kept): {node_id} ({node_name})")
        elif is_favorite:
            favorites_count += 1
            print(f"[⭐] Keeping favorite: {node_id} ({node_name})")
        elif via_mqtt:
            old_nodes_count += 1
            nodes_to_remove.append(node_id)
            print(f"[🗑️] Will remove (MQTT node): {node_id} ({node_name})")
        elif time_since_heard > SIX_DAYS_SECONDS:
            old_nodes_count += 1
            nodes_to_remove.append(node_id)
            if last_heard:
                print(f"[🗑️] Will remove (last heard {days_since_heard:.1f} days ago): {node_id} ({node_name})")
            else:
                print(f"[🗑️] Will remove (never heard): {node_id} ({node_name})")
        else:
            print(f"[⏰] Keeping recent node (last heard {days_since_heard:.1f} days ago): {node_id} ({node_name})")
    
    print(f"[📈] Cleanup summary:")
    print(f"  - Favorite nodes kept: {favorites_count}")
    print(f"  - Recent nodes kept: {len(nodes) - favorites_count - old_nodes_count - 1}")  # -1 for own node
    print(f"  - Nodes to remove (MQTT + >6 days old): {len(nodes_to_remove)}")
    print(f"  - Own node (always kept): 1")
    
    if not nodes_to_remove:
        print("[✅] No nodes need to be removed!")
        last_run_time = time.time()
        return
    
    # Remove nodes automatically
    removed_count = 0
    for node_id in nodes_to_remove:
        try:
            # Use the proper removeNode method from the interface
            node_num = nodes[node_id].get('num')
            if node_num:
                interface.localNode.removeNode(node_num)
                removed_count += 1
                print(f"[🗑️] Removed node: {node_id}")
            else:
                print(f"[⚠️] Could not find numeric ID for {node_id}")
            
        except Exception as e:
            print(f"[⚠️] Failed to remove {node_id}: {e}")
    
    print(f"[✅] Cleanup complete! Removed {removed_count} nodes.")
    print("[💡] Note: Changes may take a moment to reflect in the device.\n")
    
    # Update last run time
    last_run_time = time.time()


def get_info():
    """Return information about this action."""
    return {
        "name": "Node DB Cleaner",
        "description": "Removes MQTT nodes and nodes not heard from in 6+ days",
        "interval_minutes": INTERVAL_SECONDS // 60,
        "last_run": last_run_time
    }
