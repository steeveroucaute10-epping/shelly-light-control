#!/usr/bin/env python3

import requests
import datetime
import schedule
import time
import yaml
import logging
import sys
import os
import socket
import json

class ShellyLightController:
    def __init__(self, config_path):
        # Load configuration
        with open(config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file']),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Configuration parameters
        self.relay_ip = self.config['shelly']['relay']['ip']
        self.light_threshold = self.config['light_control']['light_threshold']
        self.max_hour = self.config['light_control']['max_hour']
        self.check_interval = self.config['light_control']['check_interval']
        self.retry_attempts = self.config['light_control'].get('retry_attempts', 3)
        self.retry_delay = self.config['light_control'].get('retry_delay', 10)
        self.work_days = self.config['work_days']
        self.network_timeout = self.config['network'].get('timeout', 10)
        
        # State tracking
        self.lights_on = False

    def check_network_connectivity(self):
        """Check if the network is reachable."""
        try:
            socket.create_connection((self.relay_ip, 80), timeout=self.network_timeout)
            return True
        except (socket.error, socket.timeout):
            self.logger.warning(f"Network connectivity to {self.relay_ip} failed")
            return False

    def get_light_level(self):
        """Retrieve light level from Shelly device with robust error handling."""
        for attempt in range(self.retry_attempts):
            try:
                # Shelly 1 PM Mini Gen 4 status URL (may need adjustment)
                url = f"http://{self.relay_ip}/status"
                response = requests.get(url, timeout=self.network_timeout)
                
                # Validate response
                if response.status_code != 200:
                    raise ValueError(f"HTTP error: {response.status_code}")
                
                # Parse JSON response
                data = response.json()
                
                # Extract light level (this may need to be adjusted based on actual Shelly API)
                # Common paths might be: data.get('light'), data.get('sensors', {}).get('light')
                light_level = data.get('light')
                
                if light_level is None:
                    self.logger.warning(f"Could not extract light level. Full response: {data}")
                    raise ValueError("Light level not found in response")
                
                self.logger.info(f"Light level retrieved: {light_level} lux")
                return light_level
            
            except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
                self.logger.error(f"Light level retrieval attempt {attempt + 1} failed: {e}")
                
                # Network connectivity check
                if not self.check_network_connectivity():
                    self.logger.critical("Network connectivity lost. Waiting before retry.")
                    time.sleep(self.retry_delay)
                
                # Wait before next attempt
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        # All attempts failed
        self.logger.error("Failed to retrieve light level after all attempts")
        return None

    def is_work_day(self):
        """Check if today is a configured work day."""
        today = datetime.datetime.now().weekday()
        return today in self.work_days

    def control_lights(self):
        """Main light control logic with comprehensive error handling."""
        # Check work day constraint
        if not self.is_work_day():
            self.logger.debug("Not a work day. Skipping light control.")
            return

        # Check time constraint
        current_time = datetime.datetime.now()
        if current_time.hour >= self.max_hour:
            self.logger.debug(f"Time is after {self.max_hour}:00. Skipping light control.")
            return

        # Retrieve light level
        light_level = self.get_light_level()
        if light_level is None:
            # If light level retrieval fails, log and potentially take a safe action
            self.logger.warning("Could not determine light level. Skipping light control.")
            return

        try:
            # Implement hysteresis for light control
            if not self.lights_on and light_level < self.light_threshold:
                # Turn lights on
                url = f"http://{self.relay_ip}/relay/0?turn=on"
                response = requests.get(url, timeout=self.network_timeout)
                
                if response.status_code == 200:
                    self.lights_on = True
                    self.logger.info(f"Lights turned ON. Light level: {light_level} lux")
                else:
                    self.logger.error(f"Failed to turn lights on. Status code: {response.status_code}")
            
            elif self.lights_on and light_level > (self.light_threshold + 20):  # Hysteresis buffer
                # Turn lights off
                url = f"http://{self.relay_ip}/relay/0?turn=off"
                response = requests.get(url, timeout=self.network_timeout)
                
                if response.status_code == 200:
                    self.lights_on = False
                    self.logger.info(f"Lights turned OFF. Light level: {light_level} lux")
                else:
                    self.logger.error(f"Failed to turn lights off. Status code: {response.status_code}")
        
        except requests.RequestException as e:
            self.logger.error(f"Network error while controlling lights: {e}")

    def start_monitoring(self):
        """Start monitoring light levels and controlling lights."""
        self.logger.info("Starting Shelly Light Controller")
        
        # Schedule light control checks
        schedule.every(self.check_interval).minutes.do(self.control_lights)
        
        # Run initial check
        self.control_lights()
        
        # Continuous monitoring
        while True:
            schedule.run_pending()
            time.sleep(1)

def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    controller = ShellyLightController(config_path)
    
    try:
        controller.start_monitoring()
    except KeyboardInterrupt:
        print("\nLight controller stopped.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()