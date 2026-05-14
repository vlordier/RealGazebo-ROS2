import json
from dora import Node

def main():
    node = Node()
    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "pose":
                data = json.loads(event["value"][0].as_py())
                print(f"[dora] Vehicle: x={data['x']:.2f} y={data['y']:.2f} z={data['z']:.2f}")
            elif event["id"] == "tick":
                node.send_output("status", json.dumps({"running": True}).encode())

if __name__ == "__main__":
    main()
