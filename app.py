"""
HEOS Dashboard - Main Application
Connects configuration, API, and stations modules to provide web interface
"""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import json
import tempfile

# Import configuration
from config import setup_configuration, save_config, check_device_connection, get_device_info, discover_and_update_device_info

# Import HEOS API
from heos_api import HeosDevice

# Import station management
from stations import StationManager

# Initialize configuration
config = setup_configuration()

# Initialize Flask application
app = Flask(__name__)

# Initialize device connection
device = HeosDevice(config["device"]["ip"], config["device"]["port"])

# Initialize station manager
station_manager = StationManager(config["app"]["stations_file"])

@app.route("/", methods=["GET"])
def index():
    """Render the main dashboard page"""
    device_name = config["device"]["friendly_name"]
    device_model = config["device"]["model"]
    
    # Check if device is online
    connection_status = "online" if device.check_connection() else "offline"
    
    # Get current volume
    current_volume = device.get_volume()
    
    return render_template(
        "dashboard.html", 
        stations=station_manager.stations,
        current_volume=current_volume,
        current_station=request.args.get('station', ''),
        device_name=device_name,
        device_model=device_model,
        connection_status=connection_status
    )

@app.route("/preset_play", methods=["POST"])
def preset_play():
    """Play a preset station"""
    uri = request.form.get("uri")
    station_name = request.form.get("name")
    
    if uri:
        device.set_uri(uri)
        device.play()
    
    # Redirect to home with station name parameter
    return redirect(url_for('index', station=station_name))

@app.route("/play", methods=["POST"])
def play():
    """Start playback"""
    device.play()
    return redirect(url_for('index'))

@app.route("/pause", methods=["POST"])
def pause():
    """Pause playback"""
    device.pause()
    return redirect(url_for('index'))

@app.route("/stop", methods=["POST"])
def stop():
    """Stop playback"""
    device.stop()
    return redirect(url_for('index'))

@app.route("/setvolume", methods=["POST"])
def set_volume():
    """Set volume level"""
    level = request.form.get("level")
    if level:
        device.set_volume(level)
    return redirect(url_for('index'))

@app.route("/poweroff", methods=["POST"])
def power_off():
    """Power off the device"""
    device.power_off()
    return redirect(url_for('index'))

@app.route("/manage_stations", methods=["GET"])
def manage_stations():
    """Render station management page"""
    return render_template("manage_stations.html", stations=station_manager.stations)

@app.route("/add_station", methods=["POST"])
def add_station():
    """Add a new station"""
    try:
        name = request.form.get("name")
        uri = request.form.get("uri")
        
        if not name or not uri:
            return jsonify({"success": False, "message": "Name and URI are required"}), 400
        
        station_manager.add_station(name, uri)
        return redirect(url_for('manage_stations'))
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/remove_station", methods=["POST"])
def remove_station():
    """Remove a station"""
    try:
        name = request.form.get("name")
        
        if not name:
            return jsonify({"success": False, "message": "Station name is required"}), 400
        
        station_manager.remove_station(name)
        return redirect(url_for('manage_stations'))
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/remove_multiple_stations", methods=["POST"])
def remove_multiple_stations():
    """Remove multiple stations"""
    try:
        data = request.json
        names = data.get('names', [])
        
        if not names:
            return jsonify({"success": False, "message": "No station names provided"}), 400
        
        result = station_manager.remove_stations(names)
        
        if result:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "message": "Failed to remove stations"}), 500
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/export_stations", methods=["GET"])
def export_stations():
    """Export stations to JSON file for download"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_filename = tmp.name
            # Write stations to the temp file
            json.dump(station_manager.stations, tmp, indent=2)
        
        # Send the file to the client
        return send_file(
            tmp_filename,
            as_attachment=True,
            download_name="heos_stations.json",
            mimetype="application/json"
        )
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/import_stations", methods=["POST"])
def import_stations():
    """Import stations from JSON file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400
        
        file = request.files['file']
        
        # Check if file is empty
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Check if file is JSON
        if not file.filename.endswith('.json'):
            return jsonify({"success": False, "message": "Only JSON files are supported"}), 400
        
        # Save file to temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(temp_file.name)
        temp_file.close()
        
        # Get replace flag
        replace = 'replace' in request.form
        
        # Import stations
        try:
            # Read the JSON from temp file
            with open(temp_file.name, 'r') as f:
                stations_data = json.load(f)
            
            # Validate the JSON format
            if not all(isinstance(s, dict) and 'name' in s and 'uri' in s for s in stations_data):
                raise ValueError("Invalid station format in JSON file")
            
            # Add stations
            if replace:
                station_manager._stations = stations_data
                station_manager.save()
            else:
                # Add each station
                for station in stations_data:
                    station_manager.add_station(station['name'], station['uri'])
            
        finally:
            # Clean up the temp file
            os.unlink(temp_file.name)
        
        return redirect(url_for('manage_stations'))
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/settings", methods=["GET"])
def settings():
    """Render settings page"""
    return render_template("settings.html", config=config)

@app.route("/update_device_config", methods=["POST"])
def update_device_config():
    """Update device configuration"""
    try:
        ip = request.form.get("ip")
        port = request.form.get("port")
        friendly_name = request.form.get("friendly_name")
        
        if not ip or not port:
            return jsonify({"success": False, "message": "IP and port are required"})
        
        # Update config
        config["device"]["ip"] = ip
        config["device"]["port"] = int(port)
        if friendly_name:
            config["device"]["friendly_name"] = friendly_name
        
        # Save config
        if save_config(config):
            # Update device connection
            global device
            device = HeosDevice(ip, int(port))
            
            return jsonify({"success": True, "reload": True})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/update_app_config", methods=["POST"])
def update_app_config():
    """Update application configuration"""
    try:
        port = request.form.get("port")
        host = request.form.get("host")
        debug = "debug" in request.form
        
        # Update config
        if port:
            config["app"]["port"] = int(port)
        if host:
            config["app"]["host"] = host
        config["app"]["debug"] = debug
        
        # Save config
        if save_config(config):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/update_ui_config", methods=["POST"])
def update_ui_config():
    """Update UI configuration"""
    try:
        theme = request.form.get("theme")
        default_volume = request.form.get("default_volume")
        
        # Update config
        if theme:
            config["ui"]["theme"] = theme
        if default_volume:
            config["ui"]["default_volume"] = int(default_volume)
        
        # Save config
        if save_config(config):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/update_config", methods=["POST"])
def update_config():
    """Update configuration from AJAX requests"""
    try:
        data = request.json
        
        # Update config with the provided data
        for section, values in data.items():
            if section in config:
                for key, value in values.items():
                    if key in config[section]:
                        config[section][key] = value
        
        # Save config
        if save_config(config):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/test_connection", methods=["POST"])
def test_connection():
    """Test connection to the device"""
    try:
        data = request.json
        ip = data.get("ip")
        port = data.get("port")
        
        if not ip or not port:
            return jsonify({"success": False, "message": "IP and port are required"})
        
        # Create temporary device connection
        temp_device = HeosDevice(ip, int(port))
        
        # Check connection
        if temp_device.check_connection():
            # Try to get device info
            device_info = get_device_info(ip, int(port))
            
            return jsonify({
                "success": True, 
                "device_info": device_info if any(device_info.values()) else None
            })
        else:
            return jsonify({"success": False, "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/rediscover_device", methods=["POST"])
def rediscover_device():
    """Rediscover device information"""
    try:
        # Get current device info
        global config
        
        # Try to discover device information
        updated_config = discover_and_update_device_info(config)
        
        if updated_config != config:
            config = updated_config
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "No new device information discovered"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# Run the application when executed directly
if __name__ == "__main__":
    # Get app settings from config
    host = config["app"]["host"]
    port = config["app"]["port"]
    debug = config["app"]["debug"]
    
    print(f"\n🎶 HEOS Dashboard starting up...")
    print(f"Device: {config['device']['friendly_name']} ({config['device']['ip']}:{config['device']['port']})")
    print(f"Server: http://{host}:{port}")
    print(f"Debug mode: {'On' if debug else 'Off'}")
    print(f"Default theme: {config['ui']['theme'].capitalize()}")
    print(f"Loaded {len(station_manager.stations)} stations\n")
    
    app.run(debug=debug, port=port, host=host)