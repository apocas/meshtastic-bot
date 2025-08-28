# Meshtastic Bot

A modular, extensible bot for Meshtastic devices that automates tasks and interactions on your mesh network.

## What it Does

This bot connects to a Meshtastic node via a serial connection and runs a series of "actions" based on incoming packets or a timed schedule. It's designed to be easily extensible, allowing you to create your own custom actions to fit your needs.

## How it Works

The bot is driven by an `ActionManager` that dynamically loads and executes Python scripts from the `actions/` directory. Each script represents a distinct action.

There are two main ways actions are triggered:

1. **Packet-based:** The action is triggered by an incoming packet from the Meshtastic network.
2. **Time-based:** The action runs on a regular, timed interval.

The core components are:

- `main.py`: The entry point of the application. It handles the connection to the Meshtastic device, initializes the database, and starts the action manager.
- `actions/manager.py`: This class is responsible for discovering, loading, and executing the actions.
- `actions/`: This directory contains the individual action scripts.

## Features

- **Dynamic Action Loading:** Simply drop a Python script into the `actions/` directory, and the bot will load it automatically.
- **SQLite Database:** A simple database is used to persist data, such as keeping track of nodes seen on the network.
- **Environment-based Configuration:** The bot uses a `.env` file to manage configuration, making it easy to set up without modifying the code.
- **Automatic Reconnection:** The bot automatically detects connection failures and reconnects to maintain continuous operation.
- **Comprehensive Logging:** Built-in logging system tracks all bot activities, errors, and action executions for debugging and monitoring.
- **Multiple Connection Types:** Supports both serial (USB) and IP/TCP connections to Meshtastic devices.

## Getting Started

### Prerequisites

- A Meshtastic device connected to your computer.
- Python 3.11 or higher.

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ZSTelmo/meshtastic-bot.git
   cd meshtastic-bot
   ```

2. **Install the dependencies:**

   ```bash
   pip install -e .
   ```

3. **Configure the bot:**

   - Create a `.env` file in the root of the project. You can copy the example file:

     ```bash
     cp .env.example .env
     ```

   - Edit the `.env` file to configure your connection settings and logging preferences:
     - `CONNECTION_TYPE`: Set to "serial" or "ip"
     - `PORT`: Serial port for USB connections (e.g., `/dev/ttyUSB0`)
     - `DEVICE_IP`: IP address for TCP connections
     - `LOG_LEVEL`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR)
     - `LOG_FILE`: Path to log file (default: `meshbot.log`)

4. **Run the bot:**

   ```bash
   python main.py
   ```

## Logging and Monitoring

The bot includes comprehensive logging to help you monitor its operation and debug issues:

### Log Levels

- **DEBUG:** Very detailed information (heartbeats, packet details, action attempts)
- **INFO:** General operations (connections, successful action executions)
- **WARNING:** Issues that don't stop the bot (connection problems, skipped actions)
- **ERROR:** Serious errors (action failures, unexpected exceptions)

### Viewing Logs

```bash
# View live logs as they happen
tail -f meshbot.log

# Search for errors
grep ERROR meshbot.log

# Search for specific actions
grep "welcome_message" meshbot.log

# View recent connection events
grep -E "Connect|Disconnect|Reconnect" meshbot.log
```

### Configuration

Set logging preferences in your `.env` file:

```properties
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Log file location
LOG_FILE=meshbot.log
```

## Automatic Reconnection

The bot automatically handles connection issues:

- **Connection Monitoring:** Sends heartbeat signals every 30 seconds to detect dead connections
- **Automatic Retry:** If the connection is lost, the bot waits 30 seconds and attempts to reconnect
- **Graceful Error Handling:** Properly closes broken connections to prevent resource leaks
- **Continuous Operation:** The bot continues running even through multiple connection failures

## Creating Your Own Actions

Creating a new action is simple.

1. Create a new Python file in the `actions/` directory (e.g., `my_action.py`).
2. The file must contain at least two functions: `should_run()` and `execute()`.
3. Optionally, you can include a `get_info()` function to provide a name, description, and interval for your action.

### Action Structure

```python
# actions/my_action.py

def get_info():
    """
    Returns information about the action.
    """
    return {
        "name": "My Awesome Action",
        "description": "This is a description of what my action does.",
        "interval_minutes": 15  # Optional: specify how often it runs
    }

def should_run():
    """
    Determines if the action should be executed.
    Return True to run the action, False to skip.
    """
    # Example: run every 15 minutes
    from datetime import datetime
    return datetime.now().minute % 15 == 0

def execute(interface, my_node_num, **kwargs):
    """
    The main logic of the action.
    """
    print("Executing My Awesome Action!")
    # Your action logic here
    # You can use the 'interface' to send messages, etc.
```

### Available Parameters for `execute`

The `execute` function can receive the following arguments:

- `interface`: The Meshtastic `SerialInterface` object. Use this to interact with the device (e.g., `interface.sendText("Hello!")`).
- `my_node_num`: The node number of the bot's Meshtastic device.
- `packet` (optional): The packet that triggered the action (for packet-based actions).
- `conn` (optional): The SQLite database connection.
