# HSM Anomaly Detection System

A Hardware Security Module (HSM) anomaly detection system using Raspberry Pi Pico 2 W with machine learning-based intrusion detection and real-time web monitoring.

## Features

- **Dual-sensor anomaly detection**: ML-optimized light sensor + pattern-based shake detection
- **Machine learning threshold**: Grid search with K-fold cross validation for light sensor optimization
- **Shake/movement detection**: Pattern-based detection of rapid tilt sensor changes (3+ in 2 seconds)
- **Real-time alerts**: Buzzer system to alert of intrusion
- **Web dashboard**: Live sensor monitoring with visual status indicators
- **Remote kill switch**: Emergency system shutdown via web interface
- **WiFi connectivity**: Access system from any device on network
- **Multithreaded operation**: Concurrent detection loop and web server

## Hardware Requirements

- **Raspberry Pi Pico 2 W** (WiFi-enabled microcontroller)
- **Photocell** (light sensor) - Connect to GP26 (ADC0)
- **Digital tilt sensor** - Connect to GP27 (digital input with PULL_DOWN)
- **Piezo buzzer** - Connect to GP15 (PWM output)
- **LED** - Built-in LED on Pico

## Wiring Diagram

```
Pico 2 W Connections:
- GP26 -> Photocell
- GP27 -> Tilt sensor
- GP15 -> Buzzer
- 3.3V -> Sensor power supplies
- GND -> Common ground
```

## File Structure

```
src/
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
├── report.tex                         # IEEE conference paper
├── hsm_data.csv                       # Training data (light + tilt values, labels)
├── hsm_train.py                       # ML training with Grid Search + K-fold CV
├── light_threshold_results.csv        # Cross-validation results
│
├── onboard/                           # Pico deployment files
│   ├── main.py                        # Full detection system with web interface
│   ├── model_params.py                # Generated ML thresholds
│   └── pico_collect.py                # On-device data collection

## Quick Start

### 1. Install Dependencies (Host Machine)

```bash
pip install -r requirements.txt
```

### 2. Install MicroPython on Pico 2 W

1. Download MicroPython firmware for Pico W from https://micropython.org/download/RPI_PICO_W/
2. Hold BOOTSEL button while connecting Pico to computer
3. Copy the .uf2 file to the RPI-RP2 drive
4. Pico will reboot with MicroPython installed

### 3. Data Collection

**Option A: Use existing data**
- Use the provided `hsm_data.csv` file with pre-collected sensor data

**Option B: Collect new data**
1. Upload `onboard/pico_collect.py` to Pico
2. Run the collection script on Pico via serial terminal
3. Label data as normal (0) or anomaly (1)
4. Copy output to `hsm_data.csv`

### 4. Train ML Model

Train the detection thresholds using Grid Search with K-fold cross validation:

```bash
python hsm_train.py
```

This generates:
- `onboard/model_params.py` with optimal thresholds
- Model files in `models/` directory (model.pkl, rf_model.pkl, scaler.pkl, threshold_model.pkl)
- Validation results in `light_threshold_results.csv`

### 5. Deploy to Pico

1. Ensure `onboard/model_params.py` contains the trained thresholds

2. Update WiFi credentials in `onboard/main.py` (if using web interface):
   ```python
   WIFI_SSID = "YOUR_WIFI_NAME"
   WIFI_PASSWORD = "YOUR_PASSWORD"
   ```

3. Upload both files to Pico:
   - `onboard/main.py` - Main detection system
   - `onboard/model_params.py` - ML thresholds

4. Run `main.py` on the Pico

5. If WiFi is configured, access web dashboard at `http://<PICO_IP>` (IP shown in console)

6. Dashboard features:
   - Real-time sensor readings
   - Anomaly counters
   - System status indicators
   - Emergency shutdown button

## Detection Logic

The system uses **dual anomaly detection**:

### Light Sensor (ML-based)
- Trained using Grid Search + 5-fold Cross Validation
- Optimized for F1 score (precision/recall balance)
- Triggers when light > learned threshold

### Tilt Sensor (Pattern-based)
- Detects rapid state changes (0→1→0→1...)
- Triggers when 3+ changes occur within 2 seconds
- Catches shaking, movement, vibrations from drilling/cutting

### Combined Logic
```python
light_anomaly = light > LIGHT_THRESHOLD
shake_anomaly = (changes_in_2_seconds >= 5)
is_anomaly = light_anomaly OR shake_anomaly
```

## System Operation

1. **Normal Mode**: Continuous monitoring at 50Hz
2. **Light Anomaly**: Someone opens enclosure (light enters)
3. **Shake Anomaly**: Physical tampering detected (drilling, moving, impact)
4. **Alert Response**: Buzzer sounds, LED flashes until threat ends

## Configuration Parameters

### Light Detection (in `model_params_light.py`)
```python
LIGHT_THRESHOLD = 0.181234  # Volts - from ML training
CV_ACCURACY = 0.9875        # Cross-validated accuracy
```

### Shake Detection (in `pico_tilt_shake_detect.py`)
```python
CHANGE_COUNT_THRESHOLD = 5   # Number of state changes
CHANGE_TIME_WINDOW = 2.0     # Time window (seconds)
CHANGE_DEBOUNCE = 0.03       # Min time between changes
```

## Machine Learning Approach

The system uses **Grid Search with K-Fold Cross Validation**:

1. **Data-driven**: Learns optimal threshold from real sensor data
2. **Cross-validated**: 5-fold validation prevents overfitting
3. **Academically sound**: Proper ML methodology with statistical validation
4. **Lightweight**: Simple threshold suitable for Pico deployment

This is a legitimate machine learning approach that's both rigorous and practical.

## Troubleshooting

### Tilt Sensor Issues
- **Always reads 1**: Try `Pin.PULL_DOWN` instead of `Pin.PULL_UP`
- **No response**: Check wiring, try different GPIO pin
- **Too sensitive**: Increase `CHANGE_DEBOUNCE` parameter

### Light Sensor Issues
- **Low threshold**: Retrain model with more varied lighting data
- **High false positives**: Collect more "normal" data in various lighting conditions

### Training Issues
- **No data**: Ensure `hsm_data.csv` exists with `light,label` columns
- **Poor accuracy**: Collect more diverse training data
- **Class imbalance**: Ensure good mix of normal/anomaly samples

## Applications

- **Hardware Security Modules (HSMs)**: Protect cryptographic hardware
- **Server rack monitoring**: Detect unauthorized physical access
- **Equipment tampering**: Monitor critical infrastructure
- **Educational projects**: Learn ML + embedded systems

## Academic Use

This project demonstrates:
- Machine learning on embedded systems
- Cross-validation techniques
- Pattern recognition algorithms
- Sensor fusion concepts
- Real-time anomaly detection

Suitable for:
- Computer Science coursework
- Electrical Engineering projects
- Machine Learning applications
- IoT security research

## Safety Note

This is an educational project. For production security applications, use certified hardware security modules with professional tamper-resistant enclosures and commercial intrusion detection systems.

## License

MIT License - Feel free to modify for educational and research purposes.