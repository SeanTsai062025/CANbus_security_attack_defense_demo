
# IoT Vehicle Security: Remote CAN Bus Attack & Defense Simulation

This project demonstrates an automotive cybersecurity implementation using a **Raspberry Pi 5**. It simulates a realistic vehicle network attack scenario, showing how a hacker can remotely control a vehicle's CAN Bus via a compromised connected device (e.g., a Wi-Fi Gateway). Furthermore, it implements a robust defense mechanism using **HMAC Signatures** and **Rolling Counters**.


---

## 📖 Project Overview

This project simulates two distinct scenarios, ranging from a completely vulnerable system to a secured architecture with a Security Gateway (Guardian).

### Scenario 1: The Attack (Unprotected)
In this scenario, the internal vehicle network (`vcan0`) lacks any authentication mechanism.
A hacker utilizes a compromised Web Gateway (`main.py`) to inject malicious CAN frames into the bus via HTTP requests, effectively spoofing the speedometer on the dashboard (ICSIM).

<img width="770" height="381" alt="圖片 1" src="https://github.com/user-attachments/assets/d7ae0fe9-0906-48a1-8a46-4b38f32f0302" />


### Scenario 2: The Defense (Secured)
In this scenario, we introduce a **Guardian (Security Gateway)** and a **Secure Sensor**.
* **Network Segmentation**: The network is split into an "Untrusted Zone" (`vcan0`) and a "Trusted Zone" (`vcan1`).
* **Authentication**: The sensor signs data using HMAC-SHA256.
* **Anti-Replay**: A Rolling Counter is implemented to prevent replay attacks.

The Guardian monitors `vcan0`, filters out forged packets from the hacker, and forwards only verified data to the dashboard located on `vcan1`.

<img width="770" height="381" alt="圖片 2" src="https://github.com/user-attachments/assets/33e61fa4-2c3a-470a-aa4f-a643038e6a4d" />


---

## 📂 Files Description

| File Name | Role | Description |
| :--- | :--- | :--- |
| **`main.py`** | 🕷️ Attacker | **The Hacked Gateway**. Runs a FastAPI server that receives remote HTTP commands and sends malicious, unsigned CAN frames. |
| **`sensor.py`** | 👴 Legacy Sensor | **Standard Sensor**. Simulates normal speed signals. Vulnerable to race conditions when the attacker is active. |
| **`sensor_secure.py`** | 🛡️ Secure Sensor | **Secure Sensor**. Sends encrypted packets containing `HMAC` signatures and `Counters` instead of raw plaintext data. |
| **`guardian.py`** | 👮 Guardian | **Security Gateway/Firewall**. Bridges `vcan0` and `vcan1`. Verifies signatures, blocks attacks, and protects the dashboard. |

---

## How to Start the Demo

### 1. Pre-requisites (Raspberry Pi)
Ensure system dependencies and the dashboard simulator are installed:

```bash
# Install system tools
sudo apt install git libsdl2-dev libsdl2-image-dev can-utils python3-pip -y

# Install and compile ICSim (Instrument Cluster Simulator)
git clone [https://github.com/zombiever/ic-sim.git](https://github.com/zombiever/ic-sim.git)
cd ic-sim && make
```

### 2. Network Setup
Configure two virtual CAN interfaces: `vcan0` (External/Insecure) and `vcan1` (Internal/Secure).

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
sudo ip link add dev vcan1 type vcan
sudo ip link set up vcan1
```

---

### 🔥 Demo A: Running the Attack
**Goal:** Demonstrate how a hacker controls the dashboard via HTTP requests.

1.  **Start the Dashboard** (Listening on `vcan0`):
    ```bash
    ./ic-sim/icsim vcan0
    ```
2.  **Start the Hacked Gateway**:
    ```bash
    python3 main.py
    # Server will start on port 8000
    ```
3.  **Execute the Attack** (From a browser or curl):
    ```bash
    # Spoof speed to 200 mph
    curl "http://<RPi_IP>:8000/attack/continuous?speed=200&duration=5"
    ```
    > **Result**: The dashboard needle will ignore the sensor and spike to 200 mph.

---

### 🛡️ Demo B: Running the Defense
**Goal:** Demonstrate how the Guardian intercepts attacks and protects the dashboard.

1.  **Start the Dashboard** (Switch listener to **vcan1** Secure Zone):
    ```bash
    ./ic-sim/icsim vcan1
    ```
2.  **Start the Guardian** (Filters `vcan0` and forwards to `vcan1`):
    ```bash
    python3 guardian.py
    ```
3.  **Start the Secure Sensor** (Sends signed data to `vcan0`):
    ```bash
    python3 sensor_secure.py
    ```
    > The dashboard should now show normal, fluctuating speed.
4.  **Attempt the Attack Again**:
    ```bash
    python3 main.py
    # Send attack request
    curl "http://<RPi_IP>:8000/attack/continuous?speed=200"
    ```
    > **Result**: The dashboard remains **unaffected** and continues to show normal speed.
    > Check the terminal running `guardian.py`; you will see red `DROP: bad HMAC` warning messages.

---

## ⚠️ Disclaimer

This project is for **EDUCATIONAL AND ACADEMIC RESEARCH PURPOSES ONLY**.
* All attack simulations are performed in a **Virtual CAN (vcan)** environment and do not involve real vehicle hardware.
* Do not apply the code or attack techniques from this project to any real vehicles or public infrastructure.
* The developers accept no liability for any damage or legal consequences resulting from the use of this project's code.

**Created for the study of Automotive Cybersecurity.**
