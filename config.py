"""
Configuration module for HEOS Dashboard
Handles loading/saving config and device discovery
"""
import os
import yaml
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import socket

# Default configuration if no config file exists
DEFAULT_CONFIG = {
    "device": {
        "ip": "10.29.60.78",
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
CONFIG_FILE = "heos_dashboard_config.yaml"

def load_config():
    """Load configuration from file or create default if not exists"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
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
            yaml.dump(config, f, default_flow_style=False)
        print(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_device_info(ip, port):
    """
    Attempt to query device information using UPnP/DLNA
    
    This tries multiple common UPnP description endpoints to find
    device information for Marantz/HEOS and similar devices.
    """
    endpoints = [
        f"http://{ip}:{port}/description.xml",
        f"http://{ip}:{port}/upnp/desc/aios_device/description.xml",
        f"http://{ip}:{port}/dlna/device.xml",
        f"http://{ip}/description.xml"  # Some devices use a different port for UPnP
    ]
    
    device_info = {
        "friendly_name": None,
        "model": None,
        "manufacturer": None
    }
    
    for endpoint in endpoints:
        try:
            print(f"Trying to fetch device info from: {endpoint}")
            response = requests.get(endpoint, timeout=3)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                
                # Try to find device element (usually under root or root/device)
                device_element = root.find(".//device")
                if device_element is None:
                    continue
                
                # Extract information if available
                friendly_name_elem = device_element.find("friendlyName")
                model_elem = device_element.find("modelName") or device_element.find("modelNumber")
                manufacturer_elem = device_element.find("manufacturer")
                
                if friendly_name_elem is not None and friendly_name_elem.text:
                    device_info["friendly_name"] = friendly_name_elem.text
                
                if model_elem is not None and model_elem.text:
                    device_info["model"] = model_elem.text
                    
                if manufacturer_elem is not None and manufacturer_elem.text:
                    device_info["manufacturer"] = manufacturer_elem.text
                
                # If we found at least one piece of information, return it
                if any(device_info.values()):
                    print("Device information found!")
                    return device_info
        
        except requests.RequestException as e:
            print(f"Could not connect to {endpoint}: {e}")
        except ET.ParseError as e:
            print(f"Could not parse XML from {endpoint}: {e}")
        except Exception as e:
            print(f"Unexpected error querying {endpoint}: {e}")
    
    print("Could not find device information")
    return device_info

def discover_and_update_device_info(config):
    """Discover device information and update config if found"""
    ip = config["device"]["ip"]
    port = config["device"]["port"]
    
    device_info = get_device_info(ip, port)
    
    # Update config with any discovered information
    updated = False
    for key, value in device_info.items():
        if value is not None:
            config["device"][key] = value
            updated = True
    
    if updated:
        save_config(config)
        print("Configuration updated with device information")
    
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
    config = discover_and_update_device_info(config)
    
    return config

# Example usage when run directly
if __name__ == "__main__":
    # Run this script directly to test configuration discovery
    config = setup_configuration()
    print("\nCurrent configuration:")
    print(yaml.dump(config, default_flow_style=False))
    
    # Test connection
    ip = config["device"]["ip"]
    port = config["device"]["port"]
    if check_device_connection(ip, port):
        print(f"✓ Connection to {ip}:{port} successful")
    else:
        print(f"✗ Could not connect to {ip}:{port}")