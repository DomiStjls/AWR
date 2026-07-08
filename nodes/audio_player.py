#!/usr/bin/env python3

import os
import io
import wave
import threading

import pyaudio
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

SOUNDS = {
    "GOAL SUCCESS": "success.wav",
    "GOAL CANCELLED": "cancel.wav",
    "GOAL ABORTED": "abort.wav",
    "POINT ADDED": "added.wav",
    "DEFAULT": "road.wav",
}


class AudioPlayer(Node):
    """Проигрывает WAV-файлы по событиям из топиков."""

    def __init__(self):
        super().__init__("audio_player")

        # Путь к папке со звуками (рядом со скриптом)
        self.base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "sounds"
        )
        self.get_logger().info(f"Sounds dir: {self.base_dir}")

        # Проверяем наличие файлов
        for event, filename in SOUNDS.items():
            path = os.path.join(self.base_dir, filename)
            if os.path.exists(path):
                self.get_logger().info(f"OK: {filename}")
            else:
                self.get_logger().warn(f"Missing: {filename}")

        # Подписки
        self.create_subscription(String, "/goal/status", self.on_goal, 10)
        self.create_subscription(String, "/dj_msc", self.on_point, 10)

        self.get_logger().info("Audio player ready")

    #  Воспроизведение

    def play(self, filepath: str, block: bool = False):
        """Проигрывает WAV-файл. block=True — ждать окончания."""

        def _play():
            pa = pyaudio.PyAudio()
            try:
                with open(filepath, "rb") as f:
                    data = f.read()

                with io.BytesIO(data) as buf, wave.open(buf, "rb") as wf:
                    stream = pa.open(
                        format=pa.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                    )
                    chunk = wf.readframes(1024)
                    while chunk:
                        stream.write(chunk)
                        chunk = wf.readframes(1024)
                    stream.stop_stream()
                    stream.close()
            except Exception as e:
                self.get_logger().error(f"Playback error: {e}")
            finally:
                pa.terminate()

        if block:
            _play()
        else:
            threading.Thread(target=_play, daemon=True).start()

    def _play_event(self, event: str):
        """Проигрывает звук по ключу события, если файл найден."""
        filename = SOUNDS.get(event, SOUNDS["DEFAULT"])
        filepath = os.path.join(self.base_dir, filename)

        self.get_logger().info(f"Playing: {event} -> {filename}")

        if os.path.exists(filepath):
            self.play(filepath, block=False)
        else:
            self.get_logger().error(f"Not found: {filepath}")

    #  Обработчики событий

    def on_goal(self, msg: String):
        """Статус достижения цели: SUCCESS / CANCELLED / ABORTED."""
        self._play_event(msg.data)

    def on_point(self, msg: String):
        """События точек маршрута: POINT ADDED и др."""
        self._play_event(msg.data)


def main(args=None):
    rclpy.init(args=args)
    node = AudioPlayer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
