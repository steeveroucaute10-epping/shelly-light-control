#!/usr/bin/env python3

import requests
import subprocess
import json
import sys

def find_shelly_device(mac_address):
    """Find Shelly device on the network using MAC address."""
    try:
        # Use arp-scan to find IP for the given MAC
        print("Running arp-scan...")
        arp_result = subprocess.check_output(['sudo', 'arp-scan', '--localnet'], universal_newlines=True)
        print("ARP Scan Results:")
        print(arp_result)
        
        for line in arp_result.splitlines():
            print(f"Checking line: {line}")
            if mac_address.lower() in line.lower():
                ip = line.split()[0]
                print(f"Found device IP: {ip}")
                return ip
        
        print(f"No device found with MAC {mac_address}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {e}")
        print(f"Error output: {e.output}")
        return None
    except Exception as e:
        print(f"Unexpected error finding device with MAC {mac_address}: {e}")
        return None

def test_shelly_api(ip):
    """Test Shelly device API and retrieve available information."""
    try:
        # Try multiple potential API endpoints for Shelly Gen 4 devices
        endpoints = [
            f"http://{ip}/rpc/Shelly.GetStatus",
            f"http://{ip}/status",
            f"http://{ip}/rpc/DeviceInfo.GetStatus"
        ]
        
        for endpoint in endpoints:
            try:
                print(f"🔍 Trying endpoint: {endpoint}")
                response = requests.get(endpoint, timeout=5)
                print(f"📡 Status code: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        json_response = response.json()
                        print(f"\n✅ Successful API call to {endpoint}")
                        
                        # Detailed parsing for Gen 4 devices
                        print("\n📊 Device Information:")
                        
                        # Print key device details
                        if 'mac' in json_response:
                            print(f"🖥️ MAC Address: {json_response.get('mac', 'N/A')}")
                        
                        if 'device_status' in json_response:
                            device_status = json_response['device_status']
                            print(f"🔌 Power Status: {device_status.get('is_on', 'Unknown')}")
                            
                            # Power monitoring
                            if 'power' in device_status:
                                print(f"⚡ Current Power: {device_status['power']} W")
                        
                        # Attempt to find environmental data
                        if 'sensors' in json_response:
                            sensors = json_response['sensors']
                            print("\n🌡️ Sensor Data:")
                            for sensor, value in sensors.items():
                                print(f"  {sensor.capitalize()}: {value}")
                        
                        # Detailed JSON for reference
                        print("\n🔬 Full JSON Response:")
                        print(json.dumps(json_response, indent=2))
                        
                        return json_response
                    
                    except json.JSONDecodeError:
                        print(f"❌ Could not decode JSON from {endpoint}")
            
            except requests.RequestException as e:
                print(f"❌ Request to {endpoint} failed: {e}")
        
        print("❌ No successful Shelly API endpoints found.")
        return None
    
    except Exception as e:
        print(f"❌ Unexpected error testing Shelly API: {e}")
        return None

def scan_all_ips(start_ip='192.168.4.1', end_ip='192.168.4.255'):
    """Scan all IPs in a range and test Shelly API."""
    import ipaddress
    
    start = ipaddress.ip_address(start_ip)
    end = ipaddress.ip_address(end_ip)
    
    current = start
    while current <= end:
        ip_str = str(current)
        print(f"\n🔍 Checking IP: {ip_str}")
        test_result = test_shelly_api(ip_str)
        if test_result:
            print(f"🎉 Potential Shelly device found at {ip_str}")
        
        current = ipaddress.ip_address(int(current) + 1)

def main():
    # First, try to find by MAC
    mac_address = "c0:2c:ed:a9:05:41"
    print(f"Searching for Shelly device with MAC: {mac_address}")
    
    device_ip = find_shelly_device(mac_address)
    if device_ip:
        print(f"Found device IP: {device_ip}")
        test_shelly_api(device_ip)
    else:
        print("MAC-based discovery failed. Scanning all IPs...")
        scan_all_ips()

if __name__ == "__main__":
    main()