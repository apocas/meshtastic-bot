"""
Welcome Message Action

This action sends a welcome message to new RF nodes that haven't been seen before.
It runs on every packet receive (no interval).
"""

import time
import sqlite3
import os


def should_run():
    """This action should only run when a packet is received (packet-based action)."""
    return False  # Never run in time-based mode


def should_run_on_packet():
    """This action should run when a packet is received."""
    return True


def execute(interface, my_node_num, packet=None, conn=None):
    """Execute the welcome message action."""
    
    # Skip if no packet or database connection provided
    if not packet or not conn:
        print(f"[DEBUG] Welcome action: No packet ({packet is not None}) or no conn ({conn is not None})")
        return
    
    try:
        from_node = packet.get("from")
        print(f"[DEBUG] Welcome action: Processing packet from node {from_node}")
        
        if not from_node or from_node == my_node_num:
            print(f"[DEBUG] Welcome action: Ignoring packet from own node or invalid node")
            return  # Ignore own messages

        # ✅ Must be a direct RF packet
        if packet.get("rxRssi") is None or packet.get("rxSnr") is None:
            print(f"[DEBUG] Welcome action: Ignoring MQTT/non-RF packet from node {from_node}")
            return  # Skip non-RF packets

        print(f"[DEBUG] Welcome action: Valid RF packet from node {from_node} (RSSI: {packet.get('rxRssi')}, SNR: {packet.get('rxSnr')})")

        # Check if we've already seen this node
        if has_seen_node(conn, from_node):
            print(f"[📶] Already seen node {from_node}")
            return

        # Welcome new RF node
        welcome_msg = os.getenv("WELCOME_MSG", "Welcome to Meshtastic!")
        
        print(f"[🆕] New RF node seen: {from_node}")
        print("[📦] Raw packet:", packet)
        
        interface.sendText(welcome_msg, destinationId=from_node)
        store_node(conn, from_node, packet)
        
    except Exception as e:
        print(f"[❌] Error in welcome message action: {e}")


def has_seen_node(conn, node_id):
    """Check if we've already seen this node."""
    c = conn.cursor()
    c.execute("SELECT 1 FROM nodes WHERE node_id = ?", (node_id,))
    return c.fetchone() is not None


def store_node(conn, node_id, packet):
    """Store new node in database."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO nodes (node_id, raw_json)
        VALUES (?, ?)
    """, (node_id, str(packet)))
    conn.commit()


def get_info():
    """Return information about this action."""
    return {
        "name": "Welcome Message Sender",
        "description": "Sends welcome messages to new RF nodes",
        "interval_minutes": "On demand",
        "last_run": "N/A"
    }
