import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface
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
CONNECTION_TYPE = os.getenv("CONNECTION_TYPE", "serial")
DEVICE_IP = os.getenv("DEVICE_IP")

my_node_num = None
conn = None
action_manager = None

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

# -- Handle incoming packets --
def on_receive(packet=None, interface=None):
    global my_node_num, conn, action_manager
    try:
        if not packet or not interface:
            return

        # Run packet-based actions (like ping-pong and welcome messages)
        action_manager.run_actions(interface, my_node_num, packet=packet, conn=conn)

    except Exception as e:
        print(f"[‼] Error: {e}")

def main():
    global my_node_num, conn, action_manager

    print("[🔌] Connecting to Meshtastic device...")
    iface = None
    if CONNECTION_TYPE == "serial":
        print(f"[*] Connecting to {PORT} via serial...")
        iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
    elif CONNECTION_TYPE == "ip":
        if not DEVICE_IP:
            print("[‼] Error: CONNECTION_TYPE is 'ip' but DEVICE_IP is not set in .env file.")
            return
        print(f"[*] Connecting to {DEVICE_IP} via IP...")
        iface = meshtastic.tcp_interface.TCPInterface(hostname=DEVICE_IP)
    else:
        print(f"[‼] Error: Unknown CONNECTION_TYPE '{CONNECTION_TYPE}'. Must be 'serial' or 'ip'.")
        return

    if not iface:
        print("[‼] Error: Could not connect to Meshtastic device.")
        return

    my_node_num = iface.myInfo.my_node_num
    print(f"[🆔] This node ID: {my_node_num}")

    conn = init_db()

    # Initialize action manager
    action_manager = ActionManager()

    pub.subscribe(on_receive, "meshtastic.receive")
    
    print("[] Waiting for new RF nodes...")
    print("[⚙️] Actions loaded and ready...")
    
    # Show loaded actions info
    actions_info = action_manager.get_actions_info()
    for action_name, info in actions_info.items():
        interval = info.get('interval_minutes', 'N/A')
        print(f"[] {info.get('name', action_name)}: {info.get('description', 'No description')} (Every {interval} min)")
    
    try:
        while True:
            # Run time-based actions that should execute
            action_manager.run_actions(iface, my_node_num, conn=conn)
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[⛔] Exiting...")
        iface.close()
        conn.close()

if __name__ == "__main__":
    main()
