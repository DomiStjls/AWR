#!/usr/bin/env python3
"""
server_bridge.py

ROS2-нода: мост между роботом и веб-сервером WMS.
- Получает обнаруженные метки регистрирует точки на сервере
- Отправляет статус робота раз в секунду
- Запрашивает задачи и публикует целевые координаты
"""

import requests
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

SERVER_BASE = "https://lucidly-liked-egret.cloudpub.ru"


class ServerBridge(Node):
    """Мост: ROS2 to HTTP WMS-сервер."""

    def __init__(self):
        super().__init__("server_bridge")

        # Эндпоинты 
        self.url_qr = f"{SERVER_BASE}/register_qr"
        self.url_status = f"{SERVER_BASE}/robot_status"
        self.url_get_task = f"{SERVER_BASE}/get_task"

        # ROS2: публикуем цели, слушаем метки 
        self.pub_response = self.create_publisher(String, "/server/response", 10)
        self.pub_goal = self.create_publisher(String, "/server/goal_position", 10)
        self.sub_request = self.create_subscription(
            String, "/server/request", self.on_marker, 10
        )

        # Таймеры 
        self.create_timer(1.0, self.send_status)
        self.create_timer(1.0, self.poll_task)

        # Состояние 
        self.status = "free"

        self.get_logger().info("Server bridge started")

    #  Регистрация точки (ArUco)

    def on_marker(self, msg: String):
        """Получает "marker_id x y" и регистрирует точку на сервере."""
        parts = msg.data.split()
        if len(parts) != 3:
            self.get_logger().warn(f"Bad marker format: {msg.data}")
            return

        payload = {
            "id": parts[0],
            "x": float(parts[1]),
            "y": float(parts[2]),
        }
        try:
            requests.post(self.url_qr, json=payload, timeout=3)
        except requests.RequestException as e:
            self.get_logger().error(f"QR register failed: {e}")

    #  Статус робота

    def send_status(self):
        """Отправляет текущий статус робота на сервер."""
        try:
            requests.post(self.url_status, json={"status": self.status}, timeout=3)
        except requests.RequestException as e:
            self.get_logger().error(f"Status send failed: {e}")

    #  Получение задачи

    def poll_task(self):
        """Если робот свободен - запрашивает задачу и публикует цель."""
        if self.status != "free":
            self.get_logger().debug("Busy, skipping task poll")
            return

        try:
            resp = requests.get(self.url_get_task, timeout=3).json()
        except requests.RequestException as e:
            self.get_logger().error(f"Task poll failed: {e}")
            return

        task = resp.get("task")
        if task is None:
            self.get_logger().info("No tasks available")
            return

        # Извлекаем координаты маршрута
        x_src = resp.get("x_src")
        y_src = resp.get("y_src")
        x_dst = resp.get("x_dst")
        y_dst = resp.get("y_dst")

        self.get_logger().info(f"New task: {task}")
        self.get_logger().info(f"Route: ({x_src}, {y_src}) > ({x_dst}, {y_dst})")

        # Публикуем цель
        goal = String()
        goal.data = f"{x_src} {y_src} {x_dst} {y_dst}"
        self.pub_goal.publish(goal)

        self.status = "work"


def main(args=None):
    rclpy.init(args=args)
    node = ServerBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
