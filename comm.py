"""
HEOS/Marantz Communication Module
Handles all device interactions using SOAP/UPnP
"""
import requests
import xml.etree.ElementTree as ET

class HeosDevice:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.control_url = f"http://{ip}:{port}/upnp/control/renderer_dvc/AVTransport"
        self.headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
        }
    
    def build_soap_envelope(self, action, service, body_xml):
        """Build SOAP envelope for UPnP requests"""
        return f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\"
            s:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\">
  <s:Body>
    <u:{action} xmlns:u=\"{service}\">
      {body_xml}
    </u:{action}>
  </s:Body>
</s:Envelope>"""

    def send_upnp_action(self, action, body_xml, service="urn:schemas-upnp-org:service:AVTransport:1", control_url=None):
        """Send UPnP action to the device"""
        if control_url is None:
            control_url = self.control_url
            
        headers = self.headers.copy()
        headers["SOAPACTION"] = f'"{service}#{action}"'
        envelope = self.build_soap_envelope(action, service, body_xml)
        
        try:
            response = requests.post(control_url, data=envelope, headers=headers, timeout=5)
            return response.text
        except requests.RequestException as e:
            print(f"Error sending UPnP action: {e}")
            return f"<error>Connection failed: {e}</error>"
    
    def set_uri(self, uri):
        """Set the URI (stream URL) for playback"""
        xml_body = f"""
        <InstanceID>0</InstanceID>
        <CurrentURI>{uri}</CurrentURI>
        <CurrentURIMetaData></CurrentURIMetaData>
        """
        return self.send_upnp_action("SetAVTransportURI", xml_body)
    
    def play(self):
        """Start playback"""
        return self.send_upnp_action("Play", "<InstanceID>0</InstanceID><Speed>1</Speed>")
    
    def stop(self):
        """Stop playback"""
        return self.send_upnp_action("Stop", "<InstanceID>0</InstanceID>")
    
    def pause(self):
        """Pause playback"""
        return self.send_upnp_action("Pause", "<InstanceID>0</InstanceID>")
    
    def power_off(self):
        """Power off the device"""
        power_service = "urn:schemas-denon-com:service:ACT:1"
        power_control_url = f"http://{self.ip}:{self.port}/ACT/control"
        return self.send_upnp_action("PutPowerState", "<Power>Off</Power>", 
                                    service=power_service, 
                                    control_url=power_control_url)
    
    def get_status(self):
        """Get the current transport state"""
        raw_xml = self.send_upnp_action("GetTransportInfo", "<InstanceID>0</InstanceID>")
        try:
            root = ET.fromstring(raw_xml)

            def find_text(tag_name):
                for elem in root.iter():
                    if elem.tag.endswith(tag_name):
                        return elem.text
                return "N/A"

            return {
                "Transport State": find_text("CurrentTransportState"),
                "Transport Status": find_text("CurrentTransportStatus"),
                "Playback Speed": find_text("CurrentSpeed")
            }

        except Exception as e:
            return {
                "Error": f"Failed to parse SOAP response: {e}",
                "Raw Response": raw_xml
            }
    
    def get_volume(self):
        """Get the current volume level"""
        control_url_vol = f"http://{self.ip}:{self.port}/upnp/control/renderer_dvc/RenderingControl"
        headers = self.headers.copy()
        headers["SOAPACTION"] = "\"urn:schemas-upnp-org:service:RenderingControl:1#GetVolume\""
        envelope = self.build_soap_envelope("GetVolume",
            "urn:schemas-upnp-org:service:RenderingControl:1",
            "<InstanceID>0</InstanceID><Channel>Master</Channel>"
        )
        
        try:
            response = requests.post(control_url_vol, data=envelope, headers=headers, timeout=5)
            root = ET.fromstring(response.text)
            for elem in root.iter():
                if elem.tag.endswith("CurrentVolume"):
                    return elem.text
        except Exception as e:
            print(f"Error getting volume: {e}")
        
        return "0"
    
    def set_volume(self, level):
        """Set the volume level"""
        control_url_vol = f"http://{self.ip}:{self.port}/upnp/control/renderer_dvc/RenderingControl"
        headers = self.headers.copy()
        headers["SOAPACTION"] = "\"urn:schemas-upnp-org:service:RenderingControl:1#SetVolume\""
        envelope = self.build_soap_envelope("SetVolume",
            "urn:schemas-upnp-org:service:RenderingControl:1",
            f"<InstanceID>0</InstanceID><Channel>Master</Channel><DesiredVolume>{level}</DesiredVolume>"
        )
        
        try:
            requests.post(control_url_vol, data=envelope, headers=headers, timeout=5)
            return True
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False
    
    def check_connection(self):
        """Check if device is reachable and responding"""
        try:
            status = self.get_status()
            return "Error" not in status
        except Exception:
            return False

# Example usage when run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python heos_api.py IP PORT [COMMAND] [ARG]")
        print("Commands: status, volume, set_volume, play, pause, stop, power_off, set_uri")
        sys.exit(1)
    
    ip = sys.argv[1]
    port = int(sys.argv[2])
    
    device = HeosDevice(ip, port)
    
    # Test connection
    if not device.check_connection():
        print(f"Could not connect to device at {ip}:{port}")
        sys.exit(1)
    
    # Process command if provided
    if len(sys.argv) >= 4:
        command = sys.argv[3]
        
        if command == "status":
            print("Device Status:")
            for key, value in device.get_status().items():
                print(f"  {key}: {value}")
        
        elif command == "volume":
            print(f"Current Volume: {device.get_volume()}")
        
        elif command == "set_volume" and len(sys.argv) >= 5:
            level = sys.argv[4]
            if device.set_volume(level):
                print(f"Volume set to {level}")
            else:
                print("Failed to set volume")
        
        elif command == "play":
            device.play()
            print("Started playback")
        
        elif command == "pause":
            device.pause()
            print("Paused playback")
        
        elif command == "stop":
            device.stop()
            print("Stopped playback")
        
        elif command == "power_off":
            device.power_off()
            print("Powered off device")
        
        elif command == "set_uri" and len(sys.argv) >= 5:
            uri = sys.argv[4]
            device.set_uri(uri)
            print(f"Set URI to: {uri}")
        
        else:
            print(f"Unknown command: {command}")
    else:
        # Just print status if no command
        print(f"Connected to device at {ip}:{port}")
        print("Current Status:")
        for key, value in device.get_status().items():
            print(f"  {key}: {value}")
        print(f"Volume: {device.get_volume()}")