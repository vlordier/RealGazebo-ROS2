import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
from dora import Node as DoraNode

class BridgeNode(Node):
    def __init__(self, dora):
        super().__init__('dora_bridge')
        self.dora = dora
        self.clock = None
        self.create_subscription(String, '/clock', self.clock_cb, 10)

    def clock_cb(self, msg):
        self.clock = msg

def main():
    rclpy.init()
    dora = DoraNode()
    bridge = BridgeNode(dora)
    count = 0
    for event in dora:
        if event["type"] == "INPUT":
            rclpy.spin_once(bridge, timeout_sec=0)
            count += 1
            if bridge.clock:
                dora.send_output("simulation_time", str(bridge.clock.data).encode())
            if count % 10 == 0:
                dora.send_output("vehicle_pose", json.dumps({"status": "listening"}).encode())

if __name__ == "__main__":
    main()
