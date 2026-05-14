#!/usr/bin/env python3
"""Vehicle monitor dora operator.

Receives typed VehiclePose data from the ros2_bridge operator
and logs status information.
"""

import json
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("vehicle_monitor")

try:
    from dora import Node as DoraNode
except ImportError:
    logger.error("dora module not found")
    sys.exit(1)


def main():
    node = DoraNode()
    logger.info("vehicle_monitor started")

    for event in node:
        try:
            if event["type"] != "INPUT":
                continue

            eid = event.get("id", "unknown")

            if eid == "pose" and event.get("value"):
                data = json.loads(event["value"][0].as_py())
                logger.info(
                    f"[Vehicle {data.get('vehicle_id', '?')}] "
                    f"pos=({data.get('x', 0):.1f}, {data.get('y', 0):.1f}, {data.get('z', 0):.1f}) "
                    f"type={data.get('vehicle_type', '?')}"
                )
                node.send_output("status", json.dumps({
                    "healthy": True,
                    "vehicles_tracked": 1,
                }).encode())

            elif eid == "sim_time" and event.get("value"):
                sim_time = event["value"][0].as_py()
                logger.debug(f"Sim time: {sim_time}")

            elif eid == "tick":
                node.send_output("status", json.dumps({
                    "healthy": True,
                    "running": True,
                }).encode())

        except Exception as e:
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
