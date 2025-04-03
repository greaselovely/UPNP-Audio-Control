"""
Configuration module for HEOS Dashboard
Handles loading/saving config and device discovery
"""
import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import socket

# Default configuration if no config file exists
DEFAULT_CONFIG = {
    "device": {
        "ip": "10.20.30.40",
        "port": 60006,
        "friendly_name": "HEOS Device",
        "model": "Unknown",
        "manufacturer": "Unknown"
    },
    "app": {
        "port": 5050,
        "host": "0.0.0.0",
        "debug": True,
        "stations_file": "stations.json"
    },
    "ui": {
        "theme": "light",
        "default_volume": 30
    }
}

# Path to the configuration file
CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from file or create default if not exists"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print(f"Configuration loaded from {CONFIG_FILE}")
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
    else:
        print(f"Config file {CONFIG_FILE} not found, creating with defaults")
        save_config(DEFAULT_CONFIG)
    
    return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

import socket
import json

def update_config_from_heos(config):
    ip = config["device"]["ip"]
    port = 1255  # HEOS CLI port

    try:
        with socket.create_connection((ip, port), timeout=3) as sock:
            sock.sendall(b'heos://player/get_players\n')
            response = sock.recv(4096).decode()

            data = json.loads(response.strip())
            if data["heos"]["result"] == "success":
                player = data["payload"][0]
                config["device"]["friendly_name"] = player["name"]
                config["device"]["model"] = player["model"]
                config["device"]["serial"] = player["serial"]
                config["device"]["version"] = player["version"]
                return config
    except Exception as e:
        print(f"[DISCOVERY ERROR] {e}")
        return config


def check_device_connection(ip, port, timeout=3):
    """Check if device is online by testing socket connection"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, int(port)))
        s.close()
        return result == 0
    except Exception as e:
        print(f"Error checking connection: {e}")
        return False

def setup_configuration():
    """Setup the application configuration"""
    # Load existing config or create default
    config = load_config()
    
    # Try to discover device information
    config = update_config_from_heos(config)
    
    return config

# Example usage when run directly
if __name__ == "__main__":
    # Run this script directly to test configuration discovery
    config = setup_configuration()
    print("\nCurrent configuration:")
    print(json.dump(config, indent=2))
    
    # Test connection
    ip = config["device"]["ip"]
    port = config["device"]["port"]
    if check_device_connection(ip, port):
        print(f"✓ Connection to {ip}:{port} successful")
    else:
        print(f"✗ Could not connect to {ip}:{port}")