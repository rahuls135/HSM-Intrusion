# HSM Anomaly Detection System

Real-time physical intrusion detection for hardware security modules using machine learning on Raspberry Pi Pico 2W.

## Features

- **Dual-sensor detection**: Light (ML-optimized threshold) + Tilt (pattern-based shake detection)
- **Machine Learning**: Grid Search with K-fold cross validation for threshold optimization
- **Web Dashboard**: Live monitoring with remote kill switch via WiFi
- **Real-time Alerts**: Buzzer and LED activation on anomaly detection

## Hardware Setup

- Raspberry Pi Pico 2W
- Photocell → GP26 (ADC0) with 10kΩ pull-down
- Digital tilt sensor → GP27 (PULL_DOWN) 
- Buzzer → GP15 (PWM)

## Quick Start

1. **Install dependencies**: `pip install -r requirements.txt`

2. **Train ML model**: `python hsm_train.py`
   - Generates optimal thresholds in `onboard/model_params.py`

3. **Deploy to Pico**:
   - Update WiFi credentials in `onboard/main.py`
   - Upload `main.py` and `model_params.py` to Pico
   - Access dashboard at `http://<PICO_IP>`

## Detection Logic

- **Light anomaly**: Sensor reading > ML threshold (box opened)
- **Shake anomaly**: 3+ tilt changes in 2 seconds (physical tampering)
- Triggers immediate buzzer/LED alert

## Project Structure

```
hsm_train.py           # ML training script
onboard/
├── main.py           # Detection system + web interface
├── model_params.py   # ML-generated thresholds
└── pico_collect.py   # Data collection utility
```

Academic project demonstrating embedded ML, sensor fusion, and IoT security concepts.