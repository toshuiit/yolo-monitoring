
# Dog Detection and Door Monitoring System

This project provides an automated system to monitor doors and detect dogs using YOLO models. Alerts are sent to admins if any violations are detected.

## Features

- Dog detection using YOLO.
- Door state detection: Open, Closed, Partially Open/Closed.
- ROI (Region of Interest) calculation.
- Admin alerts on violations.
- Bounding box creation using Label Studio.
- Systemd service support for Ubuntu.

## Requirements

- Ubuntu OS
- Python 3.10+
- YOLO model files
- Label Studio (for annotation)
- Required Python libraries (install via `requirements.txt`)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/toshuiit/yolo-monitoring.git
cd yolo-monitoring
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up Label Studio for bounding box annotation:

```bash
label-studio start
```

4. Configure your YOLO model paths in the code.

## Systemd Service Setup

1. Copy service files to `/etc/systemd/system/`:

```bash
sudo cp dog_live_kd.service /etc/systemd/system/
sudo cp dog_live_rm101.service /etc/systemd/system/
sudo cp door_open.service /etc/systemd/system/
```

2. Reload systemd and enable services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dog_live_kd.service
sudo systemctl enable dog_live_rm101.service
sudo systemctl enable door_open.service
```

3. Start services:

```bash
sudo systemctl start dog_live_kd.service
sudo systemctl start dog_live_rm101.service
sudo systemctl start door_open.service
```
4. Set Permissions:

```bash
chmod +x start_dog_live_kd.sh
chmod +x start_dog_live_rm101.sh
chmod +x start_door_open.sh
```

## Usage

- Annotate images using Label Studio to create bounding boxes for dogs and doors.
- Run the systemd services to continuously monitor video streams.
- Admins receive alerts via email or preferred notification channel when violations occur.

