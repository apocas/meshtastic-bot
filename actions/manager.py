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
from pathlib import Path


class ActionManager:
    def __init__(self):
        self.actions = {}
        self.load_actions()
    
    def load_actions(self):
        """Dynamically load all actions from the actions directory."""
        actions_dir = Path(__file__).parent
        
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
                    print(f"[✅] Loaded action: {info.get('name', module_name)}")
                else:
                    print(f"[⚠️] Skipped {module_name}: missing required functions (should_run, execute)")
                    
            except Exception as e:
                print(f"[❌] Failed to load action {module_name}: {e}")
    
    def run_actions(self, interface, my_node_num, packet=None, conn=None):
        """Check and run all actions that should execute."""
        for action_name, action_module in self.actions.items():
            try:
                if action_module.should_run():
                    # Check if action accepts packet and/or conn parameters
                    import inspect
                    sig = inspect.signature(action_module.execute)
                    kwargs = {}
                    
                    if 'packet' in sig.parameters:
                        kwargs['packet'] = packet
                    if 'conn' in sig.parameters:
                        kwargs['conn'] = conn
                    
                    action_module.execute(interface, my_node_num, **kwargs)
            except Exception as e:
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
        self.actions.clear()
        self.load_actions()
