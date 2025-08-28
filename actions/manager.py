"""
Action Manager for Meshtastic Bot

Dynamically loads and manages actions from the actions directory.
Each action should have:
- should_run() -> bool: Check if action should execute
- execute(interface, my_node_num): Execute the action
- get_info() -> dict: Return action information (optional)
"""

import os
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ActionManager:
    def __init__(self):
        self.actions = {}
        self.load_actions()
    
    def load_actions(self):
        """Dynamically load all actions from the actions directory."""
        actions_dir = Path(__file__).parent
        
        logger.info(f"Loading actions from {actions_dir}")
        print(f"[⚙️] Loading actions from {actions_dir}")
        
        # Find all Python files in the actions directory
        for file_path in actions_dir.glob("*.py"):
            if file_path.name.startswith("__") or file_path.name == "manager.py":
                continue  # Skip __init__.py and __pycache__
            
            module_name = file_path.stem
            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Check if module has required functions
                if hasattr(module, 'should_run') and hasattr(module, 'execute'):
                    self.actions[module_name] = module
                    info = module.get_info() if hasattr(module, 'get_info') else {"name": module_name}
                    logger.info(f"Loaded action: {info.get('name', module_name)}")
                    print(f"[✅] Loaded action: {info.get('name', module_name)}")
                else:
                    logger.warning(f"Skipped {module_name}: missing required functions (should_run, execute)")
                    print(f"[⚠️] Skipped {module_name}: missing required functions (should_run, execute)")
                    
            except Exception as e:
                logger.error(f"Failed to load action {module_name}: {e}")
                print(f"[❌] Failed to load action {module_name}: {e}")
    
    def run_actions(self, interface, my_node_num, packet=None, conn=None):
        """Check and run all actions that should execute."""
        for action_name, action_module in self.actions.items():
            try:
                should_execute = False
                
                if packet is not None:
                    # Packet-based execution: check if action handles packets
                    if hasattr(action_module, 'should_run_on_packet'):
                        should_execute = action_module.should_run_on_packet()
                    # Legacy support for actions that don't have should_run_on_packet
                    # but only if should_run() returns True AND the action accepts packets
                    elif not hasattr(action_module, 'should_run_on_packet'):
                        if hasattr(action_module, 'should_run') and action_module.should_run():
                            # Only run if the action explicitly checks for packets
                            import inspect
                            sig = inspect.signature(action_module.execute)
                            if 'packet' in sig.parameters:
                                should_execute = True
                else:
                    # Time-based execution: use should_run() function
                    if hasattr(action_module, 'should_run'):
                        should_execute = action_module.should_run()
                
                if should_execute:
                    logger.debug(f"Running action: {action_name}")
                    # Check if action accepts packet and/or conn parameters
                    import inspect
                    sig = inspect.signature(action_module.execute)
                    kwargs = {}
                    
                    if 'packet' in sig.parameters:
                        kwargs['packet'] = packet
                    if 'conn' in sig.parameters:
                        kwargs['conn'] = conn
                    
                    # Execute the action
                    result = action_module.execute(interface, my_node_num, **kwargs)
                    
                    # Only log success for meaningful executions
                    if packet is not None:
                        # For packet-based actions, only log if we're processing a valid packet
                        logger.debug(f"Completed packet-based action: {action_name}")
                    else:
                        # For time-based actions, always log successful execution
                        logger.info(f"Successfully executed time-based action: {action_name}")
            except Exception as e:
                logger.error(f"Error running action {action_name}: {e}")
                print(f"[❌] Error running action {action_name}: {e}")
    
    def get_actions_info(self):
        """Get information about all loaded actions."""
        info = {}
        for action_name, action_module in self.actions.items():
            if hasattr(action_module, 'get_info'):
                info[action_name] = action_module.get_info()
            else:
                info[action_name] = {"name": action_name, "description": "No description available"}
        return info
    
    def reload_actions(self):
        """Reload all actions (useful for development)."""
        logger.info("Reloading all actions...")
        self.actions.clear()
        self.load_actions()
