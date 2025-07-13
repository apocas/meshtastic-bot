#!/usr/bin/env python3
"""
Manual Node Database Cleaner

This script connects to a Meshtastic device and removes ALL nodes from the
node database except favorites and your own node.

Unlike the automated cleaner, this removes ALL non-favorite nodes regardless 
of age or MQTT status.

Usage: python manual_clean.py
"""

import meshtastic
import meshtastic.serial_interface
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PORT = os.getenv("PORT", "/dev/ttyUSB0")

def manual_clean_nodedb():
    """Manually clean the node database, keeping only favorite nodes and own node."""
    
    print("🧹 Manual Node Database Cleaner")
    print("================================")
    print("⚠️  WARNING: This will remove ALL non-favorite nodes!")
    print("Only your own node and favorites will be kept.\n")
    
    # Ask for confirmation
    response = input("❓ Are you sure you want to proceed? (y/N): ").strip().lower()
    if response != 'y':
        print("⛔ Operation cancelled.")
        return
    
    print("\n[🔌] Connecting to Meshtastic device...")
    try:
        iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
    except Exception as e:
        print(f"[❌] Failed to connect to device: {e}")
        return
    
    my_node_num = iface.myInfo.my_node_num
    print(f"[🆔] This node ID: {my_node_num}")
    
    # Get current nodes
    nodes = iface.nodes
    print(f"[📊] Total nodes in database: {len(nodes)}")
    
    favorites_count = 0
    nodes_to_remove = []
    
    # Identify nodes to keep (favorites + own) and nodes to remove
    for node_id, node_data in nodes.items():
        is_favorite = node_data.get('isFavorite', False)
        is_own_node = node_data.get('num') == my_node_num
        node_name = node_data.get('user', {}).get('longName', 'Unknown')
        
        if is_own_node:
            print(f"[🏠] Own node (always kept): {node_id} ({node_name})")
        elif is_favorite:
            favorites_count += 1
            print(f"[⭐] Keeping favorite: {node_id} ({node_name})")
        else:
            nodes_to_remove.append(node_id)
            print(f"[🗑️] Will remove: {node_id} ({node_name})")
    
    print(f"\n[📈] Summary:")
    print(f"  - Favorite nodes to keep: {favorites_count}")
    print(f"  - Nodes to remove: {len(nodes_to_remove)}")
    print(f"  - Own node (always kept): 1")
    
    if not nodes_to_remove:
        print("[✅] No nodes need to be removed!")
        iface.close()
        return
    
    # Final confirmation for destructive action
    print(f"\n⚠️  FINAL WARNING: About to remove {len(nodes_to_remove)} nodes!")
    response = input("❓ Type 'DELETE' to confirm (case sensitive): ").strip()
    if response != 'DELETE':
        print("⛔ Operation cancelled.")
        iface.close()
        return
    
    print(f"\n[🔄] Starting manual cleanup of {len(nodes_to_remove)} nodes...")
    
    # Remove nodes
    removed_count = 0
    failed_count = 0
    
    for node_id in nodes_to_remove:
        try:
            # Use the proper removeNode method from the interface
            node_num = nodes[node_id].get('num')
            if node_num:
                iface.localNode.removeNode(node_num)
                removed_count += 1
                print(f"[🗑️] Removed node: {node_id}")
            else:
                print(f"[⚠️] Could not find numeric ID for {node_id}")
                failed_count += 1
            
        except Exception as e:
            print(f"[⚠️] Failed to remove {node_id}: {e}")
            failed_count += 1
    
    print(f"\n[✅] Manual cleanup complete!")
    print(f"  - Successfully removed: {removed_count} nodes")
    print(f"  - Failed to remove: {failed_count} nodes")
    print(f"  - Nodes remaining: {favorites_count + 1} (favorites + own node)")
    print("[💡] Note: Changes may take a moment to reflect in the device.")
    
    iface.close()

def main():
    """Main entry point."""
    try:
        manual_clean_nodedb()
    except KeyboardInterrupt:
        print("\n[⛔] Operation interrupted by user.")
    except Exception as e:
        print(f"[❌] Unexpected error: {e}")

if __name__ == "__main__":
    main()
