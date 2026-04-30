#!/usr/bin/env python3

import requests
import subprocess
import json
import sys

def find_shelly_device(mac_address):
    """Find Shelly device on the network using MAC address."""
    try:
        # Use arp-scan to find IP for the given MAC
        arp_result = subprocess.check_output(['sudo', 'arp-scan', '--localnet'], universal_newlines=True)
        for line in arp_result.splitlines():
            if mac_address.lower() in line.lower():
                ip = line.split()[0]
                return ip
    except Exception as e:
        print(f"Error finding device with MAC {mac_address}: {e}")
        return None

def test_shelly_api(ip):
    """Test Shelly device API and retrieve available information."""
    try:
        # Try multiple potential API endpoints
        endpoints = [
            f"http://{ip}/status",
            f"http://{ip}/rpc/Shelly.GetStatus",
            f"http://{ip}/rpc/Light.GetStatus"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    print(f"\nSuccessful API call to {endpoint}")
                    print("Response JSON:")
                    print(json.dumps(response.json(), indent=2))
                    return response.json()
            except requests.RequestException:
                continue
        
        print("No successful API endpoints found.")
        return None
    
    except Exception as e:
        print(f"Error testing Shelly API: {e}")
        return None

def main():
    mac_address = "c0:2c:ed:a9:05:41"
    print(f"Searching for Shelly device with MAC: {mac_address}")
    
    device_ip = find_shelly_device(mac_address)
    if not device_ip:
        print("Device not found on network.")
        sys.exit(1)
    
    print(f"Found device IP: {device_ip}")
    test_shelly_api(device_ip)

if __name__ == "__main__":
    main()