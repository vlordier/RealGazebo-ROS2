"""Benchmark tests for RealGazebo data models and network_sim performance."""

import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'realgazebo-dora', 'ros2-bridge')
)

from ros2_bridge.datamodel import V2VQuality, VehiclePose


def benchmark_v2v_construct(n: int = 100000) -> float:
    """Time the construction of n V2VQuality models."""
    t0 = time.perf_counter()
    for _ in range(n):
        V2VQuality(
            distance_m=100.0,
            rssi_dbm=-75.0,
            packet_loss_rate=0.3,
            latency_ms=15.0,
        )
    return time.perf_counter() - t0


def benchmark_pose_json(n: int = 50000) -> float:
    """Time the serialization of n VehiclePose models to JSON."""
    pose = VehiclePose(x=10.0, y=20.0, z=-5.0, vehicle_type='x500')
    t0 = time.perf_counter()
    for _ in range(n):
        pose.to_json()
    return time.perf_counter() - t0


def main():
    print('  V2VQuality construct x100k:', end=' ')
    t = benchmark_v2v_construct()
    print(f'{t:.3f}s  ({100000 / t:.0f} ops/sec)')

    print('  VehiclePose to_json x50k:', end=' ')
    t = benchmark_pose_json()
    print(f'{t:.3f}s  ({50000 / t:.0f} ops/sec)')


if __name__ == '__main__':
    main()
