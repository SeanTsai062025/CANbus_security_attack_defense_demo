import time, random, signal, sys, can, hmac, hashlib, struct

INTERVAL = 0.2
BASE_MPH = 60
JITTER_MPH = 1.5
SPEED_CAN_ID = 0x244

RUN = True
COUNTER = 0
SECRET_KEY = b"super_secret_demo_key"

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

def compute_mac(speed100, counter):
    msg = struct.pack("!HH", speed100, counter)
    return hmac.new(SECRET_KEY, msg, hashlib.sha256).digest()[:4]

def make_signed_payload_from_mph(mph: float) -> bytes:
    global COUNTER
    # mph -> kph*100
    kph = mph / 0.6213751
    speed100 = int(kph * 100)

    COUNTER = (COUNTER + 1) & 0xFFFF

    mac = compute_mac(speed100, COUNTER)

    # byte0-1: speed100, byte2-3: counter, byte4-7: mac
    data = [0] * 8
    data[0] = (speed100 >> 8) & 0xFF
    data[1] = speed100 & 0xFF
    data[2] = (COUNTER >> 8) & 0xFF
    data[3] = COUNTER & 0xFF
    data[4:8] = mac[0:4]
    return bytes(data)

def send_speed(mph: float):
    payload = make_signed_payload_from_mph(mph)
    msg = can.Message(arbitration_id=SPEED_CAN_ID, data=payload, is_extended_id=False)
    bus.send(msg)

def shutdown(sig, frame):
    global RUN
    RUN = False

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    print("sensor_secure: sending signed speed frames to vcan0")
    try:
        while RUN:
            mph = BASE_MPH + random.uniform(-JITTER_MPH, JITTER_MPH)
            send_speed(mph)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        pass
    print("sensor_secure: stopped")
