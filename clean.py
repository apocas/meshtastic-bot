#!/usr/bin/env python3
"""
Meshtastic Node Database Cleaner

This script connects to a Meshtastic device and removes all nodes from the
node database except those marked as favorites.

Usage: python clean.py
"""

import meshtastic
import meshtastic.serial_interface
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PORT = os.getenv("PORT", "/dev/ttyUSB0")

# 6 days in seconds
SIX_DAYS_SECONDS = 6 * 24 * 60 * 60

def clean_nodedb():
    """Clean the node database, keeping only favorite nodes."""
    
    print("[🔌] Connecting to Meshtastic device...")
    try:
        iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
    except Exception as e:
        print(f"[❌] Failed to connect to device: {e}")
        return
    
    my_node_num = iface.myInfo.my_node_num
    print(f"[🆔] This node ID: {my_node_num}")
    
    # Get current nodes
    nodes = iface.nodes
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
        
        # Calculate how long ago the node was last heard
        time_since_heard = current_time - last_heard if last_heard else float('inf')
        days_since_heard = time_since_heard / (24 * 60 * 60)
        
        node_name = node_data.get('user', {}).get('longName', 'Unknown')
        
        if is_own_node:
            print(f"[🏠] Own node (always kept): {node_id} ({node_name})")
        elif is_favorite:
            favorites_count += 1
            print(f"[⭐] Keeping favorite: {node_id} ({node_name})")
        elif time_since_heard > SIX_DAYS_SECONDS:
            old_nodes_count += 1
            nodes_to_remove.append(node_id)
            if last_heard:
                print(f"[🗑️] Will remove (last heard {days_since_heard:.1f} days ago): {node_id} ({node_name})")
            else:
                print(f"[🗑️] Will remove (never heard): {node_id} ({node_name})")
        else:
            print(f"[⏰] Keeping recent node (last heard {days_since_heard:.1f} days ago): {node_id} ({node_name})")
    
    print(f"\n[📈] Summary:")
    print(f"  - Favorite nodes kept: {favorites_count}")
    print(f"  - Recent nodes kept: {len(nodes) - favorites_count - old_nodes_count - 1}")  # -1 for own node
    print(f"  - Old nodes to remove (>6 days): {len(nodes_to_remove)}")
    print(f"  - Own node (always kept): 1")
    
    if not nodes_to_remove:
        print("[✅] No nodes need to be removed!")
        iface.close()
        return
    
    print(f"\n[🔄] Starting automatic cleanup of {len(nodes_to_remove)} old nodes...")
    
    # Remove nodes automatically (no confirmation)
    removed_count = 0
    for node_id in nodes_to_remove:
        try:
            # Convert string ID to numeric if needed
            if node_id.startswith('!'):
                node_num = int(node_id[1:], 16)
            else:
                node_num = nodes[node_id].get('num')
            
            if node_num:
                print(f"[🗑️] Removing node: {node_id}")
                iface.sendText(f"admin rmnode {node_num}", destinationId=my_node_num)
                removed_count += 1
            
        except Exception as e:
            print(f"[⚠️] Failed to remove {node_id}: {e}")
    
    print(f"\n[✅] Cleanup complete! Removed {removed_count} nodes.")
    print("[💡] Note: Changes may take a moment to reflect in the device.")
    
    iface.close()

def main():
    """Main entry point."""
    print("🧹 Meshtastic Node Database Cleaner")
    print("=====================================")
    print("This will automatically remove nodes not heard in the last 6 days")
    print("(excluding favorites and your own node).\n")
    
    try:
        clean_nodedb()
    except KeyboardInterrupt:
        print("\n[⛔] Operation interrupted by user.")
    except Exception as e:
        print(f"[❌] Unexpected error: {e}")

if __name__ == "__main__":
    main()