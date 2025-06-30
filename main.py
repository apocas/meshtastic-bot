import meshtastic
import meshtastic.serial_interface
import time
import sqlite3
import os
from pubsub import pub
from dotenv import load_dotenv
from actions.manager import ActionManager

# Load environment variables from .env file
load_dotenv()

PORT = os.getenv("PORT", "/dev/ttyUSB0")
DB_PATH = os.getenv("DB_PATH", "seen_nodes.db")
WELCOME_MSG = os.getenv("WELCOME_MSG", "Welcome to Meshtastic!")

my_node_num = None

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

def main():
    global my_node_num, conn

    print("[🔌] Connecting to Meshtastic device...")
    iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)

    my_node_num = iface.myInfo.my_node_num
    print(f"[🆔] This node ID: {my_node_num}")

    conn = init_db()
    pub.subscribe(on_receive, "meshtastic.receive")

    # Initialize action manager
    action_manager = ActionManager()
    
    print("[�] Waiting for new RF nodes...")
    print("[⚙️] Actions loaded and ready...")
    
    # Show loaded actions info
    actions_info = action_manager.get_actions_info()
    for action_name, info in actions_info.items():
        interval = info.get('interval_minutes', 'N/A')
        print(f"[�] {info.get('name', action_name)}: {info.get('description', 'No description')} (Every {interval} min)")
    
    try:
        while True:
            # Run any actions that should execute
            action_manager.run_actions(iface, my_node_num)
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[⛔] Exiting...")
        iface.close()
        conn.close()

if __name__ == "__main__":
    main()
