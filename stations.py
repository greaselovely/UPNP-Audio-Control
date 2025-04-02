# stations.py
"""
Station Management Module
Handles loading, saving, and managing radio station presets
"""
import os
import pickle
import json

# Default preset stations that come with the application
DEFAULT_STATIONS = [
    {"name": "NPR", "uri": "https://npr-ice.streamguys1.com/live.mp3"},
    {"name": "Classic FM", "uri": "http://media-ice.musicradio.com/ClassicFMMP3.m3u"}
]

class StationManager:
    def __init__(self, stations_file):
        """Initialize with path to stations file"""
        self.stations_file = stations_file
        self._stations = None
        self.load()
    
    @property
    def stations(self):
        """Get the current list of stations"""
        if self._stations is None:
            self.load()
        return self._stations
    
    def load(self):
        """Load stations from file or use defaults if file doesn't exist"""
        try:
            if os.path.exists(self.stations_file):
                with open(self.stations_file, 'rb') as f:
                    self._stations = pickle.load(f)
                    print(f"Loaded {len(self._stations)} stations from {self.stations_file}")
                    return self._stations
            else:
                print(f"Stations file {self.stations_file} not found, using defaults")
                self._stations = DEFAULT_STATIONS.copy()
                self.save()
        except Exception as e:
            print(f"Error loading stations: {e}")
            self._stations = DEFAULT_STATIONS.copy()
        
        return self._stations
    
    def save(self):
        """Save stations to file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.stations_file) or '.', exist_ok=True)
            
            with open(self.stations_file, 'wb') as f:
                pickle.dump(self._stations, f)
            print(f"Saved {len(self._stations)} stations to {self.stations_file}")
            return True
        except Exception as e:
            print(f"Error saving stations: {e}")
            return False
    
    def export_json(self, filename):
        """Export stations to JSON file for easier sharing/editing"""
        try:
            with open(filename, 'w') as f:
                json.dump(self._stations, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting stations to JSON: {e}")
            return False
    
    def import_json(self, filename, replace=False):
        """Import stations from JSON file"""
        try:
            with open(filename, 'r') as f:
                imported = json.load(f)
                
            # Validate format
            if not all('name' in station and 'uri' in station for station in imported):
                raise ValueError("Invalid station format in JSON file")
                
            if replace:
                self._stations = imported
            else:
                # Merge with existing stations, avoiding duplicates by name
                existing_names = {s['name'] for s in self._stations}
                for station in imported:
                    if station['name'] not in existing_names:
                        self._stations.append(station)
                        existing_names.add(station['name'])
            
            self.save()
            return True
        except Exception as e:
            print(f"Error importing stations from JSON: {e}")
            return False
    
    def add_station(self, name, uri):
        """Add a new station or update existing one with the same name"""
        # Check if station with same name already exists
        for i, station in enumerate(self._stations):
            if station['name'] == name:
                # Update existing station
                self._stations[i] = {"name": name, "uri": uri}
                self.save()
                return True
        
        # Add new station
        self._stations.append({"name": name, "uri": uri})
        self.save()
        return True
    
    def remove_station(self, name):
        """Remove a station by name"""
        initial_count = len(self._stations)
        self._stations = [s for s in self._stations if s['name'] != name]
        
        if len(self._stations) < initial_count:
            self.save()
            return True
        return False
    
    def remove_stations(self, names):
        """Remove multiple stations by name"""
        if not names:
            return False
            
        initial_count = len(self._stations)
        self._stations = [s for s in self._stations if s['name'] not in names]
        
        if len(self._stations) < initial_count:
            self.save()
            return True
        return False
    
    def get_station(self, name):
        """Get a station by name"""
        for station in self._stations:
            if station['name'] == name:
                return station
        return None
    
    def reset_to_defaults(self):
        """Reset to default stations"""
        self._stations = DEFAULT_STATIONS.copy()
        self.save()
        return True

# Example usage when run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        stations_file = "stations.pkl"
    else:
        stations_file = sys.argv[1]
    
    manager = StationManager(stations_file)
    
    print("\nCurrent Stations:")
    for i, station in enumerate(manager.stations):
        print(f"{i+1}. {station['name']} - {station['uri']}")
    
    # Example of exporting to JSON
    export_file = "stations.json"
    if manager.export_json(export_file):
        print(f"\nExported stations to {export_file}")