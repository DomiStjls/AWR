#!/usr/bin/env python3
"""
route_builder.py

Интерактивный сбор точек маршрута через TF.
Команды:
  a — добавить текущую позицию робота
  s — сохранить в файл
  q — выход
"""

import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import TransformListener, Buffer
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException


class RouteBuilder(Node):
    def __init__(self):
        super().__init__("route_builder")

        # TF для получения позиции робота
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Публикуем событие "точка добавлена" для аудио-ноды
        self.pub_audio = self.create_publisher(String, "/dj_msc", 10)

        self.points = []
        self.running = True
        self.save_path = "RoutPoints.txt"

        # Ввод команд в фоне, чтобы не блокировать spin
        self.input_thread = threading.Thread(target=self.input_loop, daemon=True)
        self.input_thread.start()

        self.get_logger().info("Route builder ready. Commands: a=add, s=save, q=quit")

    def input_loop(self):
        while self.running:
            cmd = input("\n[a]dd  [s]ave  [q]uit\n> ").strip().lower()

            if cmd == "q":
                self.running = False
                rclpy.shutdown()
                break

            elif cmd == "a":
                self.add_point()

            elif cmd == "s":
                self.save_points()

            else:
                self.get_logger().info("Unknown command")

    def add_point(self):
        try:
            t = self.tf_buffer.lookup_transform("map", "base_link", rclpy.time.Time())

            pos = t.transform.translation
            rot = t.transform.rotation
            point = (pos.x, pos.y, pos.z, rot.x, rot.y, rot.z, rot.w)

            self.points.append(point)
            self.get_logger().info(f"Added: ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")

            # Сигнал аудио-ноде
            msg = String()
            msg.data = "POINT ADDED"
            self.pub_audio.publish(msg)

        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().error(f"TF error: {e}")

    def save_points(self):
        if not self.points:
            self.get_logger().warn("No points to save")
            return

        lines = [f"({','.join(str(v) for v in p)})" for p in self.points]
        output = "[" + ",".join(lines) + "]"

        with open(self.save_path, "w") as f:
            f.write(output)

        self.get_logger().info(f"Saved {len(self.points)} points to {self.save_path}")


def main():
    rclpy.init()
    node = RouteBuilder()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
