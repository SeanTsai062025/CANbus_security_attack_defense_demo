# guardian.py -- CAN Guardian with HMAC + counter (vcan0 -> vcan1)

import can
import hmac
import hashlib
import struct
import signal
import sys
import logging

RED = "\033[91m"
RESET = "\033[0m"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("guardian")


SPEED_CAN_ID = 0x244
SECRET_KEY = b"super_secret_demo_key"

#start vcan channels
IN_CHANNEL = "vcan0" 
OUT_CHANNEL = "vcan1"

RUN = True
last_counter = -1


def compute_mac(speed100: int, counter: int) -> bytes:
    """
    ?? HMAC tag (?? 4 bytes)
    message = [speed100, counter] ? big-endian ??
    """
    msg = struct.pack("!HH", speed100, counter)  # 2 bytes + 2 bytes = 4 bytes
    full_mac = hmac.new(SECRET_KEY, msg, hashlib.sha256).digest()
    return full_mac[:4]


def parse_signed_frame(data: bytes):
    if len(data) != 8:
        return None

    speed100 = (data[0] << 8) | data[1]
    counter = (data[2] << 8) | data[3]
    recv_mac = data[4:8]
    return speed100, counter, recv_mac


def make_icsim_payload(speed100: int) -> bytes:
    data = [0] * 8
    high = (speed100 >> 8) & 0xFF
    low = speed100 & 0xFF
    data[3] = high
    data[4] = low
    return bytes(data)


def shutdown(sig, frame):
    global RUN
    RUN = False
    log.info("Shutting down guardian...")


def main():
    global last_counter

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info("Starting CAN Guardian: vcan0 -> vcan1 with HMAC + counter")
    log.info("Listening on %s, forwarding to %s", IN_CHANNEL, OUT_CHANNEL)

    bus_in = can.interface.Bus(channel=IN_CHANNEL, bustype="socketcan")
    bus_out = can.interface.Bus(channel=OUT_CHANNEL, bustype="socketcan")

    while RUN:
        msg = bus_in.recv(timeout=1.0)
        if msg is None:
            continue

        if msg.arbitration_id != SPEED_CAN_ID:
            try:
                bus_out.send(msg)
            except Exception as e:
                log.error("Failed to forward non-speed frame: %s", e)
            continue

        parsed = parse_signed_frame(msg.data)
        if parsed is None:
            log.warning("DROP: invalid data length from 0x%x", msg.arbitration_id)
            continue

        speed100, counter, recv_mac = parsed

        expected_mac = compute_mac(speed100, counter)

        # 1) HMAC
        if recv_mac != expected_mac:
            log.warning(
                RED + "DROP: bad HMAC (id=0x%x speed100=%d counter=%d)" + RESET,
                msg.arbitration_id, speed100, counter
            )
            continue

        # 2) counter
        if counter <= last_counter:
            log.warning(
                "DROP: replay / old counter (id=0x%x speed100=%d counter=%d last=%d)",
                msg.arbitration_id, speed100, counter, last_counter
            )
            continue

        last_counter = counter

        # 3) ICSim vcan1
        out_payload = make_icsim_payload(speed100)
        out_msg = can.Message(
            arbitration_id=SPEED_CAN_ID,
            data=out_payload,
            is_extended_id=False
        )

        try:
            bus_out.send(out_msg)
            log.info(
                "FORWARD: speed=%.2f kph (counter=%d) to vcan1",
                speed100 / 100.0, counter
            )
        except Exception as e:
            log.error("Failed to send to vcan1: %s", e)

    log.info("Guardian stopped.")


if __name__ == "__main__":
    main()
