import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image

from lifecycle_msgs.srv import ChangeState, GetState
from lifecycle_msgs.msg import Transition, State

import cv2
import numpy as np

from image_viewer.encoding import (
    ENCODING_CONFIG, RGB_CHANNEL_COUNT,
    LIFECYCLE_SERVICE_TIMEOUT_S,
    GET_STATE_TIMEOUT_S,
    OPENCV_WAITKEY_MS,
)


class ImageSubscriber(Node):

    def __init__(self):
        super().__init__('image_viewer')
        self.declare_parameter('vehicle_num', 0)
        self.declare_parameter('vehicle_type', 'x500')
        self.declare_parameter('camera_type', 'front')

        self.vehicle_num = self.get_parameter('vehicle_num').get_parameter_value().integer_value
        self.vehicle_type = self.get_parameter('vehicle_type').get_parameter_value().string_value
        self.camera_type = self.get_parameter('camera_type').get_parameter_value().string_value

        self.get_logger().info(
            f"[img] Configured: {self.vehicle_type}_{self.vehicle_num} camera={self.camera_type}"
        )

        receiver_node_name = (
            f'image_receiver_{self.vehicle_type}_{self.vehicle_num}_{self.camera_type}'
        )

        self.cli = self.create_client(ChangeState, f'/{receiver_node_name}/change_state')
        if not self.cli.wait_for_service(timeout_sec=LIFECYCLE_SERVICE_TIMEOUT_S):
            raise RuntimeError('ChangeState service not available')

        self.req = ChangeState.Request()

        get_state_cli = self.create_client(GetState, f'/{receiver_node_name}/get_state')
        if not get_state_cli.wait_for_service(timeout_sec=GET_STATE_TIMEOUT_S):
            self.get_logger().warn("[img] GetState service not available, skipping lifecycle")

        future = get_state_cli.call_async(GetState.Request())
        rclpy.spin_until_future_complete(self, future)
        result = future.result()
        current_state = result.current_state.id if result else State.PRIMARY_STATE_UNKNOWN

        self.get_logger().info(f"[img] image_receiver state: {current_state}")

        if current_state == State.PRIMARY_STATE_UNCONFIGURED:
            self._lifecycle_transition(Transition.TRANSITION_CONFIGURE)
            self._lifecycle_transition(Transition.TRANSITION_ACTIVATE)
        elif current_state == State.PRIMARY_STATE_INACTIVE:
            self._lifecycle_transition(Transition.TRANSITION_ACTIVATE)
        elif current_state == State.PRIMARY_STATE_ACTIVE:
            self.get_logger().info('[img] Already active')

        topic = (
            f'/vehicle{self.vehicle_num + 1}'
            f'/camera/{self.camera_type}/image_raw'
        )
        self.subscription = self.create_subscription(
            Image, topic, self.listener_callback, qos_profile_sensor_data
        )
        self.get_logger().info(f"[img] Subscribed to {topic}")

    def _lifecycle_transition(self, transition_id: int):
        self.req.transition.id = transition_id
        future = self.cli.call_async(self.req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def listener_callback(self, msg):
        try:
            channels, conversion = ENCODING_CONFIG.get(
                msg.encoding, (RGB_CHANNEL_COUNT, None)
            )

            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                (msg.height, msg.width, channels)
            )

            if conversion is not None:
                frame = cv2.cvtColor(frame, conversion)

            window_name = f"vehicle{self.vehicle_num + 1}/{self.camera_type}"
            cv2.imshow(window_name, frame)
            cv2.waitKey(OPENCV_WAITKEY_MS)

        except Exception as e:
            self.get_logger().error(f"[img] Display failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    image_subscriber = ImageSubscriber()
    try:
        rclpy.spin(image_subscriber)
    except KeyboardInterrupt:
        pass
    finally:
        image_subscriber.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
