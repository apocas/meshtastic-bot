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
        # Debug: Show all text messages
        if packet.get('decoded', {}).get('portnum') == 'TEXT_MESSAGE_APP':
            message_text = packet.get('decoded', {}).get('payload', b'').decode('utf-8', errors='ignore').strip()
            from_node = packet.get("from")
            to_node = packet.get("to")
            
            print(f"[📱] Text message received:")
            print(f"    From: {from_node}")
            print(f"    To: {to_node} (My node: {my_node_num})")
            print(f"    Message: '{message_text}'")
            print(f"    Is direct to me: {to_node == my_node_num}")
            
            # Check if it's a ping message
            if message_text.lower() == 'ping':
                # Don't respond to our own messages
                if from_node == my_node_num:
                    print(f"[🏓] Ignoring ping from myself")
                    return
                
                # Check if it's a direct message (destinationId should be our node)
                if to_node != my_node_num:
                    print(f"[🏓] Ping not directed to me (to: {to_node}, me: {my_node_num})")
                    return
                
                print(f"[🏓] Received ping from {from_node}, responding with pong")
                
                # Send pong response with enhanced error checking and timing
                _send_pong_response(interface, from_node)
        
        # Also check if this is not a text message but we got a packet
        elif packet.get('decoded'):
            portnum = packet.get('decoded', {}).get('portnum', 'UNKNOWN')
            from_node = packet.get("from")
            print(f"[📦] Non-text packet: {portnum} from {from_node}")
            
    except Exception as e:
        print(f"[❌] Error in ping-pong action: {e}")
        import traceback
        traceback.print_exc()


def _send_pong_response(interface, from_node):
    """Send pong response with multiple retry attempts."""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Debug the node ID format
            print(f"[🔍] Attempt {attempt + 1}: From node type: {type(from_node)}, value: {from_node}")
            
            # Ensure we're using the right format for destinationId
            dest_id = from_node
            if isinstance(from_node, str) and from_node.startswith('!'):
                # Convert hex string to int if needed
                dest_id = int(from_node[1:], 16)
                print(f"[🔍] Converted destination ID: {dest_id}")
            
            # Add progressive delay between attempts
            if attempt > 0:
                delay = 0.5 * attempt  # 0.5s, 1.0s delays
                print(f"[⏳] Waiting {delay}s before retry...")
                time.sleep(delay)
            else:
                # Small initial delay to avoid overwhelming the device
                time.sleep(0.2)
            
            # Check device status before sending
            if not hasattr(interface, 'myInfo') or interface.myInfo is None:
                print(f"[⚠️] Device not properly connected on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    print(f"[❌] Device connection issues persist after {max_attempts} attempts")
                    return
            
            result = interface.sendText("pong", destinationId=dest_id)
            print(f"[🏓] Pong sent to {dest_id} (attempt {attempt + 1}) - Send result: {result}")
            
            # Check if send was successful
            if result is not None and result != 0:
                print(f"[✅] Pong successfully sent on attempt {attempt + 1}")
                time.sleep(0.1)  # Small delay after successful send
                return
            else:
                print(f"[⚠️] Send result indicates failure: {result}")
                if attempt < max_attempts - 1:
                    print(f"[🔄] Will retry in next attempt...")
                    continue
            
        except Exception as send_error:
            print(f"[❌] Attempt {attempt + 1} failed to send pong: {send_error}")
            if attempt == max_attempts - 1:
                import traceback
                traceback.print_exc()
            else:
                print(f"[🔄] Will retry...")
    
    print(f"[�] All {max_attempts} attempts to send pong failed")


def get_info():
    """Return information about this action."""
    return {
        "name": "Ping Pong Responder",
        "description": "Responds to 'ping' direct messages with 'pong'",
        "interval_minutes": "On demand",
        "last_run": "N/A"
    }
