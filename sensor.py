import time, random, signal, sys
import can

INTERVAL = 0.2
BASE_MPH = 60
JITTER_MPH = 1.5 
SPEED_POS = 3
SPEED_CAN_ID = 0x244
RUN = True

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

def make_payload_kph_from_mph(mph:int):
    kph = mph / 0.6213751
    kph100 = int(kph * 100)
    high = (kph100 >> 8) & 0xFF
    low  = kph100 & 0xFF
    data = [0]*8
    data[SPEED_POS] = high
    data[SPEED_POS+1] = low
    return bytes(data)

def send_speed(mph):
    payload = make_payload_kph_from_mph(mph)
    msg = can.Message(arbitration_id=SPEED_CAN_ID, data=payload, is_extended_id=False)
    bus.send(msg)

def shutdown(sig, frame):
    global RUN
    RUN = False

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    print("sensor_sim: starting, sending baseline speed to vcan0")
    try:
        while RUN:
            mph = BASE_MPH + random.uniform(-JITTER_MPH, JITTER_MPH)
            send_speed(mph)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        pass
    print("sensor_sim: stopped")

