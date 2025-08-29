import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface
import time
import sqlite3
import os
import logging
from datetime import datetime
from pubsub import pub
from dotenv import load_dotenv
from actions.manager import ActionManager

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "meshbot.log")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)

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

        logger.debug(f"Received packet from node {packet.get('from', 'unknown')}")
        
        # Run packet-based actions (like ping-pong and welcome messages)
        if action_manager:
            action_manager.run_actions(interface, my_node_num, packet=packet, conn=conn)

    except Exception as e:
        logger.error(f"Error in on_receive: {e}")
        print(f"[‼] Error in on_receive: {e}")

def main():
    global my_node_num, conn, action_manager

    logger.info("Starting Meshtastic Bot...")
    conn = init_db()
    action_manager = ActionManager()

    while True:
        iface = None
        try:
            logger.info("Connecting to Meshtastic device...")
            print("[🔌] Connecting to Meshtastic device...")
            if CONNECTION_TYPE == "serial":
                logger.info(f"Connecting to {PORT} via serial...")
                print(f"[*] Connecting to {PORT} via serial...")
                iface = meshtastic.serial_interface.SerialInterface(devPath=PORT)
            elif CONNECTION_TYPE == "ip":
                if not DEVICE_IP:
                    logger.error("CONNECTION_TYPE is 'ip' but DEVICE_IP is not set in .env file.")
                    print("[‼] Error: CONNECTION_TYPE is 'ip' but DEVICE_IP is not set in .env file.")
                    return
                logger.info(f"Connecting to {DEVICE_IP} via IP...")
                print(f"[*] Connecting to {DEVICE_IP} via IP...")
                iface = meshtastic.tcp_interface.TCPInterface(hostname=DEVICE_IP)
            else:
                logger.error(f"Unknown CONNECTION_TYPE '{CONNECTION_TYPE}'. Must be 'serial' or 'ip'.")
                print(f"[‼] Error: Unknown CONNECTION_TYPE '{CONNECTION_TYPE}'. Must be 'serial' or 'ip'.")
                return

            if not iface:
                logger.error("Could not connect to Meshtastic device.")
                print("[‼] Error: Could not connect to Meshtastic device.")
                print("[🔁] Retrying in 30 seconds...")
                time.sleep(30)
                continue

            my_node_num = iface.myInfo.my_node_num
            logger.info(f"Connected! Node ID: {my_node_num}")
            print(f"[🆔] This node ID: {my_node_num}")

            # Unsubscribe to prevent duplicate handlers on reconnect, then subscribe
            try:
                pub.unsubscribe(on_receive, "meshtastic.receive")
            except Exception:
                pass  # Ignore if not subscribed
            pub.subscribe(on_receive, "meshtastic.receive")
            
            logger.info("Bot is ready and waiting for packets...")
            print("[] Waiting for new RF nodes...")
            print("[⚙️] Actions loaded and ready...")
            
            actions_info = action_manager.get_actions_info()
            for action_name, info in actions_info.items():
                interval = info.get('interval_minutes', 'N/A')
                logger.info(f"Loaded action: {info.get('name', action_name)} - {info.get('description', 'No description')} (Every {interval} min)")
                print(f"[] {info.get('name', action_name)}: {info.get('description', 'No description')} (Every {interval} min)")
            
            # Main loop
            last_heartbeat_time = time.time()
            heartbeat_count = 0
            while True:
                # Run time-based actions that should execute
                action_manager.run_actions(iface, my_node_num, conn=conn)

                # Send a heartbeat every 30 seconds to check connection
                if time.time() - last_heartbeat_time > 30:
                    heartbeat_count += 1
                    logger.debug(f"Sending heartbeat #{heartbeat_count}")
                    iface.sendHeartbeat() # This will raise an exception if the connection is dead
                    last_heartbeat_time = time.time()
                
                time.sleep(1)

        except (OSError, ConnectionError, BrokenPipeError) as e:
            logger.warning(f"Connection error: {e}. Reconnecting in 30 seconds...")
            print(f"\n[💥] Connection error: {e}. Reconnecting in 30 seconds...")
            try:
                if iface:
                    iface.close()
            except (BrokenPipeError, OSError):
                logger.debug("Ignored error while closing broken connection")
                pass  # Ignore errors if the connection is already broken
            time.sleep(30)
            continue
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            print("\n[⛔] Exiting...")
            try:
                if iface:
                    iface.close()
            except (BrokenPipeError, OSError):
                logger.debug("Ignored error while closing connection during shutdown")
                pass  # Ignore errors if the connection is already broken
            if conn:
                conn.close()
            break
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            print(f"\n[💥] An unexpected error occurred: {e}. Reconnecting in 30 seconds...")
            try:
                if iface:
                    iface.close()
            except (BrokenPipeError, OSError):
                logger.debug("Ignored error while closing broken connection")
                pass  # Ignore errors if the connection is already broken
            time.sleep(30)
            continue

    logger.info("Meshtastic Bot stopped.")

if __name__ == "__main__":
    main()
