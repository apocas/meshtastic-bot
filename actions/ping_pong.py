"""
Ping Pong Action

This action responds to "ping" messages with "pong" automatically.
It runs on every packet receive (no interval).
"""

import time


def should_run():
    """This action should always be ready to run (no time-based interval)."""
    return True


def execute(interface, my_node_num, packet=None):
    """Execute the ping-pong response action."""
    
    # Skip if no packet provided
    if not packet:
        return
    
    try:
        # Check if this is a text message
        if packet.get('decoded', {}).get('portnum') != 'TEXT_MESSAGE_APP':
            return
        
        # Get the message text
        message_text = packet.get('decoded', {}).get('payload', b'').decode('utf-8', errors='ignore').strip().lower()
        
        # Check if it's a ping message
        if message_text == 'ping':
            from_node = packet.get("from")
            
            # Don't respond to our own messages
            if from_node == my_node_num:
                return
            
            # Check if it's a direct message (destinationId should be our node)
            to_node = packet.get("to")
            if to_node != my_node_num:
                return  # Not a direct message to us
            
            print(f"[🏓] Received ping from {from_node}, responding with pong")
            
            # Send pong response
            interface.sendText("pong", destinationId=from_node)
            
    except Exception as e:
        print(f"[❌] Error in ping-pong action: {e}")


def get_info():
    """Return information about this action."""
    return {
        "name": "Ping Pong Responder",
        "description": "Responds to 'ping' direct messages with 'pong'",
        "interval_minutes": "On demand",
        "last_run": "N/A"
    }
