#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from tf2_ros import TransformListener, Buffer
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException
from std_msgs.msg import String


class TFListener(Node):
    """Публикует позицию робота из TF в топик /robot_position."""

    def __init__(self):
        super().__init__('tf_listener')

        # TF: буфер + слушатель для получения преобразований координат
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Публикуем позицию как строку "x y z qx qy qz qw"
        self.publisher = self.create_publisher(String, "/robot_position", 4)

        # Опрос позиции раз в секунду
        self.timer = self.create_timer(1.0, self.get_robot_pose)

    def get_robot_pose(self):
        """Читает transform map to base_link и публикует в топик."""
        try:
            transform = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time()
            )

            t = transform.transform.translation
            r = transform.transform.rotation

            msg = String()
            msg.data = f"{t.x} {t.y} {t.z} {r.x} {r.y} {r.z} {r.w}"
            self.publisher.publish(msg)

            self.get_logger().info(f'Позиция: x={t.x:.3f}, y={t.y:.3f}, z={t.z:.3f}')
            return t.x, t.y, t.z, (r.x, r.y, r.z, r.w)

        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().error(f'Ошибка TF: {e}')
            return None


def main(args=None):
    rclpy.init(args=args)
    node = TFListener()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()