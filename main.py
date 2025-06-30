import meshtastic
import meshtastic.serial_interface
import time
import sqlite3
import os
from pubsub import pub
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PORT = os.getenv("PORT", "/dev/ttyUSB0")
DB_PATH = os.getenv("DB_PATH", "seen_nodes.db")
WELCOME_MSG = os.getenv("WELCOME_MSG", "Welcome to Meshtastic!")

# Cleaning configuration
CLEAN_INTERVAL_SECONDS = 30 * 60  # 30 minutes
SIX_DAYS_SECONDS = 6 * 24 * 60 * 60  # 6 days

my_node_num = None
last_cleanup_time = 0

# -- Initialize SQLite Database --
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            node_id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            raw_json TEXT
        )
    """)
    conn.commit()
    return conn

# -- Check if we've already seen this node --
def has_seen_node(conn, node_id):
    c = conn.cursor()
    c.execute("SELECT 1 FROM nodes WHERE node_id = ?", (node_id,))
    return c.fetchone() is not None

# -- Store new node --
def store_node(conn, node_id, packet):
    c = conn.cursor()
    c.execute("""
        INSERT INTO nodes (node_id, raw_json)
        VALUES (?, ?)
    """, (node_id, str(packet)))
    conn.commit()

# -- Handle incoming packets --
def on_receive(packet=None, interface=None):
    global my_node_num, conn
    try:
        if not packet or not interface:
            return  # Debug output

        from_node = packet.get("from")
        if not from_node or from_node == my_node_num:
            return  # Ignore own messages

        # ✅ Must be a direct RF packet
        if packet.get("rxRssi") is None or packet.get("rxSnr") is None:
            print(f"[⏩] Skipping non-RF packet from {from_node}")
            return

        if has_seen_node(conn, from_node):
            print(f"[📶] Already seen node {from_node}")
            return

        print(f"[🆕] New RF node seen: {from_node}")
        print("[📦] Raw packet:", packet)
        interface.sendText(WELCOME_MSG, destinationId=from_node)
        store_node(conn, from_node, packet)

    except Exception as e:
        print(f"[‼] Error: {e}")

# -- Node Database Cleaning --
def clean_nodedb(interface):
    """Clean the node database, keeping only favorite nodes and recent RF nodes."""
    
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

def main():
    global my_node_num, conn, last_cleanup_time

    print("[🔌] Connecting to Meshtastic device...")
    iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)

    my_node_num = iface.myInfo.my_node_num
    print(f"[🆔] This node ID: {my_node_num}")

    conn = init_db()
    pub.subscribe(on_receive, "meshtastic.receive")

    # Initialize cleanup timer
    last_cleanup_time = time.time()
    
    print("[📡] Waiting for new RF nodes...")
    print("[🧹] Automatic node cleanup every 30 minutes...")
    
    try:
        while True:
            current_time = time.time()
            
            # Check if it's time to clean the node database
            if current_time - last_cleanup_time >= CLEAN_INTERVAL_SECONDS:
                clean_nodedb(iface)
                last_cleanup_time = current_time
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[⛔] Exiting...")
        iface.close()
        conn.close()

if __name__ == "__main__":
    main()
