"""
Simple data collection on Pico - upload this to the Pico
Collects sensor data and prints it for serial collection
"""

import machine
import time
from machine import Pin, ADC

# Initialize sensors
photocell = ADC(Pin(26))  # ADC0
led = Pin("LED", Pin.OUT)

print("HSM Data Collection")
print("==================")
print("1. normal")
print("2. anomaly")
label_choice = input("Select label (1 or 2): ")

if label_choice == "1":
    label = "normal"
    print("Recording NORMAL data - keep system at rest")
elif label_choice == "2":
    label = "anomaly"
    print("Recording ANOMALY data - create disturbances")
else:
    print("Invalid choice, defaulting to normal")
    label = "normal"

print(f"\nCollecting '{label}' data...")
print("Press Ctrl+C to stop\n")

# Print header
print("light,vibration,label")

while True:
    # Read sensor (convert to voltage)
    light_val = photocell.read_u16() * 3.3 / 65535
    
    # Print CSV row
    print(f"{light_val:.4f},{label}")
    
    # Blink LED to show activity
    led.toggle()
    
    # 10Hz sampling
    time.sleep(0.1)