#!/usr/bin/env python3

import requests
import datetime
import schedule
import time
import yaml
import logging
import sys
import os

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
        self.display_ip = self.config['shelly']['display']['ip']
        self.relay_ip = self.config['shelly']['relay']['ip']
        self.light_threshold = self.config['light_control']['light_threshold']
        self.max_hour = self.config['light_control']['max_hour']
        self.check_interval = self.config['light_control']['check_interval']
        self.work_days = self.config['work_days']
        
        # State tracking
        self.lights_on = False

    def is_work_day(self):
        """Check if today is a work day."""
        today = datetime.datetime.now().weekday()
        return today in self.work_days

    def get_light_level(self):
        """Retrieve light level from Shelly display."""
        try:
            # Note: Replace with actual Shelly API endpoint
            response = requests.get(f'http://{self.display_ip}/status', timeout=5)
            data = response.json()
            
            # TODO: Confirm the exact path to light level in the JSON response
            light_level = data.get('light', None)
            
            if light_level is None:
                self.logger.warning("Could not retrieve light level")
                return None
            
            self.logger.info(f"Current light level: {light_level} lux")
            return light_level
        
        except requests.RequestException as e:
            self.logger.error(f"Error getting light level: {e}")
            return None

    def control_lights(self):
        """Control lights based on work day, time, and light level."""
        # Check if it's a work day
        if not self.is_work_day():
            self.logger.debug("Not a work day. Skipping light control.")
            return

        # Check time constraint
        current_time = datetime.datetime.now()
        if current_time.hour >= self.max_hour:
            self.logger.debug(f"Time is after {self.max_hour}:00. Skipping light control.")
            return

        # Get current light level
        light_level = self.get_light_level()
        if light_level is None:
            return

        try:
            # Implement hysteresis for light control
            if not self.lights_on and light_level < self.light_threshold:
                # Turn lights on
                response = requests.get(f'http://{self.relay_ip}/relay/0?turn=on')
                self.lights_on = True
                self.logger.info(f"Turned lights ON. Light level: {light_level} lux")
            
            elif self.lights_on and light_level > (self.light_threshold + 20):  # Hysteresis buffer
                # Turn lights off
                response = requests.get(f'http://{self.relay_ip}/relay/0?turn=off')
                self.lights_on = False
                self.logger.info(f"Turned lights OFF. Light level: {light_level} lux")
        
        except requests.RequestException as e:
            self.logger.error(f"Error controlling lights: {e}")

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