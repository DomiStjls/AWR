#!/usr/bin/env python3
import os
import time
import threading

import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import TransformListener, Buffer
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException


class ArucoDetector(Node):
    """Детектор ArUco-меток по RTSP-потоку. Публикует найденные ID с координатами робота."""

    def __init__(self):
        super().__init__("aruco_detector")

        #  RTSP-источник 
        self.RTSP_URL = "rtsp://localhost:8554/cam"
        self.latest_frame = None
        self.running = True

        #  ROS2: публикуем метки, слушаем позицию робота 
        self.publisher = self.create_publisher(String, '/server/request', 10)
        self.subscriber = self.create_subscription(
            String, '/robot_position', self.on_position, 10
        )

        self.x = 0.0
        self.y = 0.0

        #  Запуск читателя кадров в фоне 
        reader = threading.Thread(target=self.frame_reader, daemon=True)
        reader.start()

        print("Ожидание потока", end="", flush=True)
        while self.latest_frame is None and self.running:
            print(".", end="", flush=True)
            time.sleep(0.3)
        print()

        if not self.running:
            exit(1)
        print("Готово")

        #  Основной цикл: 50 Гц 
        self.timer = self.create_timer(0.02, self.update)

    #  Позиция робота (из TFListener)

    def on_position(self, msg: String):
        """Обновляет координаты робота из топика /robot_position."""
        parts = msg.data.split()
        self.x = float(parts[0])
        self.y = float(parts[1])

    #  RTSP-поток

    def frame_reader(self):
        """Фоновый поток: читает кадры с камеры, переподключается при обрыве."""
        cap = cv2.VideoCapture(self.RTSP_URL, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print(f"Не удалось подключиться к {self.RTSP_URL}")
            self.running = False
            return

        print(f"Подключено: {self.RTSP_URL}")
        errors = 0

        while self.running:
            ret, frame = cap.read()
            if not ret:
                errors += 1
                if errors >= 5:
                    print("Переподключение...")
                    cap.release()
                    cap = cv2.VideoCapture(self.RTSP_URL, cv2.CAP_FFMPEG)
                    errors = 0
                continue

            errors = 0
            self.latest_frame = frame

        cap.release()

    #  Детекция меток

    def update(self):
        """Основной цикл: ищет ArUco-метки и публикует их с координатами робота."""
        if self.latest_frame is None:
            print("Кадр ещё не получен, попробуй ещё раз.")
            return

        ids = self.detect_markers()
        if ids is None:
            return

        for marker_id in ids.flatten():
            print(f"Found id: {marker_id}")
            msg = String()
            msg.data = f"{marker_id} {self.x} {self.y}"
            self.publisher.publish(msg)

    def detect_markers(self):
        """Ищет ArUco-метки на последнем кадре. Возвращает массив ID или None."""
        gray = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (640, 480))

        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(dictionary, parameters)

        _, ids, _ = detector.detectMarkers(gray)
        return ids


def main(args=None):
    rclpy.init(args=args)
    node = ArucoDetector()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()