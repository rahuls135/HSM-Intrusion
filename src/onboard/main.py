"""
HSM Anomaly Detection with Web Interface and Kill Switch
Light threshold from ML + shake detection + web control
"""

import machine
import time
import network
import socket
import json
import _thread
import sys
from machine import Pin, ADC, PWM

# WiFi Configuration
WIFI_SSID = "ssid"
WIFI_PASSWORD = "password"

# Pin definitions
PHOTOCELL_PIN = 26  # ADC0
TILT_PIN = 27       # Digital input
BUZZER_PIN = 15     # GP15

# ML-derived light threshold (update from model_params.py)
LIGHT_THRESHOLD = 0.495627

# Shake/movement detection parameters
CHANGE_COUNT_THRESHOLD = 3   # Number of state changes to trigger
CHANGE_TIME_WINDOW = 2.0     # Time window in seconds
CHANGE_DEBOUNCE = 0.05       # Minimum time between changes (50ms)

# Alert parameters
CONSECUTIVE_ALERTS = 2       # Need N consecutive anomalies for alarm
SMOOTHING_WINDOW = 3         # Light sensor smoothing

class ShakeDetectorWeb:
    def __init__(self):
        # Initialize sensors
        self.photocell = ADC(Pin(PHOTOCELL_PIN))
        self.tilt_sensor = Pin(TILT_PIN, Pin.IN, Pin.PULL_DOWN)
        
        # Initialize outputs
        self.buzzer = PWM(Pin(BUZZER_PIN))
        self.buzzer.freq(1000)
        self.buzzer.duty_u16(0)
        
        # Light sensor smoothing
        self.light_buffer = []
        
        # Shake detection state
        self.last_tilt_state = self.tilt_sensor.value()
        self.change_times = []
        self.last_change_time = 0
        
        # Alert tracking
        self.consecutive_count = 0
        self.alarm_active = False
        
        # System control
        self.system_active = True  # Can be toggled via web interface
        
        # Statistics
        self.total_readings = 0
        self.light_anomaly_count = 0
        self.shake_anomaly_count = 0
        self.total_changes = 0
        
        # Current state for web display
        self.current_state = {
            'light': 0.0,
            'tilt': 0,
            'is_anomaly': False,
            'reason': 'Normal',
            'changes_in_window': 0
        }
        
        print("HSM Detector with Web Interface Initialized")
        print(f"Light threshold: {LIGHT_THRESHOLD}V")
        print(f"Shake pattern: {CHANGE_COUNT_THRESHOLD} changes in {CHANGE_TIME_WINDOW}s")
        
    def read_light_sensor(self):
        """Read and smooth light sensor"""
        light_val = self.photocell.read_u16() * 3.3 / 65535
        
        # Add to smoothing buffer
        self.light_buffer.append(light_val)
        if len(self.light_buffer) > SMOOTHING_WINDOW:
            self.light_buffer.pop(0)
        
        # Return smoothed value
        return sum(self.light_buffer) / len(self.light_buffer)
    
    def detect_tilt_change(self):
        """Detect state changes in tilt sensor"""
        current_state = self.tilt_sensor.value()
        current_time = time.time()
        change_detected = False
        
        # Detect state change (0->1 or 1->0)
        if current_state != self.last_tilt_state:
            # Debounce - ignore changes too close together
            if current_time - self.last_change_time > CHANGE_DEBOUNCE:
                change_detected = True
                self.last_change_time = current_time
                self.total_changes += 1
        
        self.last_tilt_state = current_state
        return change_detected
    
    def update_shake_pattern(self, change_detected):
        """Track rapid changes and detect shaking/movement"""
        current_time = time.time()
        
        if change_detected:
            self.change_times.append(current_time)
        
        # Remove old changes outside the time window
        self.change_times = [t for t in self.change_times if current_time - t <= CHANGE_TIME_WINDOW]
        
        # Check if shake threshold is met
        shake_detected = len(self.change_times) >= CHANGE_COUNT_THRESHOLD
        
        if shake_detected and len(self.change_times) == CHANGE_COUNT_THRESHOLD:
            # First time hitting the threshold
            self.shake_anomaly_count += 1
            print(f"SHAKE DETECTED! ({CHANGE_COUNT_THRESHOLD} changes)")
        
        return shake_detected
    
    def detect_light_anomaly(self, light):
        """Detect light-based anomaly"""
        return light > LIGHT_THRESHOLD
    
    def update_alarm(self, is_anomaly, reason):
        """Update alarm state with debouncing"""
        if is_anomaly and self.system_active:
            self.consecutive_count += 1
            if self.consecutive_count >= CONSECUTIVE_ALERTS:
                if not self.alarm_active:
                    self.alarm_active = True
                    self.buzzer.duty_u16(32768)  # 50% duty
                    print(f"ALARM: {reason}")
        else:
            self.consecutive_count = 0
            if self.alarm_active:
                self.alarm_active = False
                self.buzzer.duty_u16(0)
    
    def detection_loop(self):
        """Main detection loop - runs in separate thread"""
        print("\nStarting detection loop...")
        
        while True:
            if self.system_active:
                # Read light sensor
                light = self.read_light_sensor()
                
                # Detect tilt state changes
                change_detected = self.detect_tilt_change()
                
                # Update shake pattern
                shake_pattern = self.update_shake_pattern(change_detected)
                
                # Detect light anomaly
                light_anomaly = self.detect_light_anomaly(light)
                
                # Overall anomaly detection
                is_anomaly = light_anomaly or shake_pattern
                
                # Determine reason
                reasons = []
                if light_anomaly:
                    reasons.append(f"Light")
                    self.light_anomaly_count += 1
                if shake_pattern:
                    reasons.append(f"Shake")
                
                reason = " + ".join(reasons) if reasons else "Normal"
                
                # Update alarm
                self.update_alarm(is_anomaly, reason)
                
                # Update statistics
                self.total_readings += 1
                
                # Update current state for web interface
                self.current_state = {
                    'light': light,
                    'tilt': self.tilt_sensor.value(),
                    'is_anomaly': is_anomaly,
                    'reason': reason,
                    'changes_in_window': len(self.change_times),
                    'system_active': self.system_active,
                    'alarm_active': self.alarm_active,
                    'total_readings': self.total_readings,
                    'light_anomalies': self.light_anomaly_count,
                    'shake_anomalies': self.shake_anomaly_count
                }
            else:
                # System is inactive - ensure alarm is off
                if self.alarm_active:
                    self.alarm_active = False
                    self.buzzer.duty_u16(0)
            
            time.sleep(0.05)  # 20Hz sampling

class WebServer:
    def __init__(self, detector):
        self.detector = detector
        self.wlan = None
        
    def connect_wifi(self):
        """Connect to WiFi network"""
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        
        if not self.wlan.isconnected():
            print(f'Connecting to {WIFI_SSID}...')
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            max_wait = 10
            while max_wait > 0:
                if self.wlan.status() < 0 or self.wlan.status() >= 3:
                    break
                max_wait -= 1
                print('Waiting for connection...')
                time.sleep(1)
        
        if self.wlan.isconnected():
            print('WiFi Connected!')
            status = self.wlan.ifconfig()
            print(f'IP: {status[0]}')
            return status[0]
        else:
            print('WiFi Connection Failed')
            return None
    
    def serve_html(self):
        """Generate HTML page with kill switch"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>HSM Intrusion Detector</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .status-card {
            background: rgba(255, 255, 255, 0.2);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .status-card h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }
        .status-card .value {
            font-size: 24px;
            font-weight: bold;
        }
        .anomaly {
            background: rgba(255, 0, 0, 0.3);
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        .kill-switch {
            text-align: center;
            margin: 40px 0;
        }
        button {
            background: #ff4444;
            color: white;
            border: none;
            padding: 20px 40px;
            font-size: 20px;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px 0 rgba(255, 68, 68, 0.5);
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px 0 rgba(255, 68, 68, 0.6);
        }
        button.inactive {
            background: #44ff44;
            box-shadow: 0 4px 15px 0 rgba(68, 255, 68, 0.5);
        }
        button.inactive:hover {
            box-shadow: 0 6px 20px 0 rgba(68, 255, 68, 0.6);
        }
        .info {
            text-align: center;
            opacity: 0.8;
            margin-top: 20px;
        }
    </style>
    <script>
        function updateData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('light').textContent = data.light.toFixed(3) + 'V';
                    document.getElementById('tilt').textContent = data.tilt;
                    document.getElementById('changes').textContent = data.changes_in_window;
                    document.getElementById('status').textContent = data.is_anomaly ? 'INTRUSION' : 'Normal';
                    document.getElementById('reason').textContent = data.reason;
                    document.getElementById('total').textContent = data.total_readings;
                    document.getElementById('light_count').textContent = data.light_anomalies;
                    document.getElementById('shake_count').textContent = data.shake_anomalies;
                    
                    // Update status card style
                    const statusCard = document.getElementById('status-card');
                    if (data.is_anomaly) {
                        statusCard.classList.add('anomaly');
                    } else {
                        statusCard.classList.remove('anomaly');
                    }
                    
                    // Update button
                    const btn = document.getElementById('killSwitch');
                    if (data.system_active) {
                        btn.textContent = 'STOP SYSTEM';
                        btn.className = '';
                    } else {
                        btn.textContent = 'START SYSTEM';
                        btn.className = 'inactive';
                    }
                });
        }
        
        function toggleSystem() {
            fetch('/toggle', { method: 'POST' })
                .then(response => response.json())
                alert('System shutdown initiated');
        }
        
        // Update every second
        setInterval(updateData, 1000);
        window.onload = updateData;
    </script>
</head>
<body>
    <div class="container">
        <h1>HSM Intrusion Detection System</h1>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>Light Sensor</h3>
                <div class="value" id="light">-</div>
            </div>
            <div class="status-card">
                <h3>Tilt Sensor</h3>
                <div class="value" id="tilt">-</div>
            </div>
            <div class="status-card">
                <h3>Changes</h3>
                <div class="value" id="changes">-</div>
            </div>
            <div class="status-card" id="status-card">
                <h3>System Status</h3>
                <div class="value" id="status">-</div>
            </div>
            <div class="status-card">
                <h3>Reason</h3>
                <div class="value" id="reason">-</div>
            </div>
            <div class="status-card">
                <h3>Total Readings</h3>
                <div class="value" id="total">-</div>
            </div>
            <div class="status-card">
                <h3>Light Anomalies</h3>
                <div class="value" id="light_count">-</div>
            </div>
            <div class="status-card">
                <h3>Shake Anomalies</h3>
                <div class="value" id="shake_count">-</div>
            </div>
        </div>
        
        <div class="kill-switch">
            <button id="killSwitch" onclick="toggleSystem()">STOP SYSTEM</button>
        </div>
        
        <div class="info">
            <p>Light threshold: """ + str(LIGHT_THRESHOLD) + """V | Shake: """ + str(CHANGE_COUNT_THRESHOLD) + """ changes in """ + str(CHANGE_TIME_WINDOW) + """s</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def handle_request(self, conn):
        """Handle HTTP requests"""
        try:
            request = conn.recv(1024).decode('utf-8')
            print(f"Request received: {request[:50]}...")  # Debug: show first 50 chars
            
            if 'GET /data' in request:
                # Return JSON data
                response_data = json.dumps(self.detector.current_state)
                response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n{response_data}"
                
            elif 'POST /toggle' in request:
                # Kill the entire program
                print("Shutdown request received - terminating program")
                # Turn off any active alarms before exit
                self.detector.buzzer.duty_u16(0)
                self.detector.led.off()
                response_data = json.dumps({"shutdown": True, "message": "Program terminated"})
                response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n{response_data}"
                conn.send(response.encode())
                conn.close()
                print("Exiting program...")
                sys.exit()
                
            else:
                # Serve HTML page
                html = self.serve_html()
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{html}"
            
            conn.send(response.encode())
        except Exception as e:
            print(f"Request error: {e}")
        finally:
            conn.close()
    
    def start_server(self):
        """Start web server"""
        ip = self.connect_wifi()
        if not ip:
            print("Failed to connect to WiFi - running without web interface")
            return
        
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        s.bind(addr)
        s.listen(1)
        
        print(f'Web server running on http://{ip}')
        print('Access this URL to control the system')
        
        while True:
            conn, addr = s.accept()
            self.handle_request(conn)

def main():
    """Main entry point"""
    print("="*50)
    print("HSM Intrusion Detection System with Web Control")
    print("="*50)
    
    # Initialize detector
    detector = ShakeDetectorWeb()
    
    # Start detection loop in separate thread
    _thread.start_new_thread(detector.detection_loop, ())
    
    # Start web server (runs in main thread)
    server = WebServer(detector)
    server.start_server()

if __name__ == "__main__":
    main()