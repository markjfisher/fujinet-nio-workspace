from __future__ import annotations

import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from amiga_emulator.ipc import find_socket, request


class IpcTests(unittest.TestCase):
    def test_request_uses_tab_separated_line_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiberry.sock"
            ready = threading.Event()

            def server() -> None:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                    listener.bind(str(path))
                    listener.listen(1)
                    ready.set()
                    connection, _ = listener.accept()
                    with connection:
                        self.assertEqual(connection.recv(128), b"SEND_KEY\t65\t1\n")
                        connection.sendall(b"OK\n")

            thread = threading.Thread(target=server)
            thread.start()
            ready.wait(1)
            self.assertEqual(request(path, "SEND_KEY", "65", "1"), "OK")
            thread.join(1)
            self.assertFalse(thread.is_alive())

    def test_find_socket_accepts_pong_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiberry.sock"
            ready = threading.Event()

            def server() -> None:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                    listener.bind(str(path))
                    listener.listen(1)
                    ready.set()
                    connection, _ = listener.accept()
                    with connection:
                        self.assertEqual(connection.recv(128), b"PING\n")
                        connection.sendall(b"PONG\n")

            thread = threading.Thread(target=server)
            thread.start()
            ready.wait(1)
            self.assertEqual(find_socket(str(path), timeout=1), path)
            thread.join(1)
            self.assertFalse(thread.is_alive())

    def test_request_accepts_reply_without_newline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amiberry.sock"
            ready = threading.Event()

            def server() -> None:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                    listener.bind(str(path))
                    listener.listen(1)
                    ready.set()
                    connection, _ = listener.accept()
                    with connection:
                        self.assertEqual(connection.recv(128), b"PING\n")
                        connection.sendall(b"PONG")
                        time.sleep(0.1)

            thread = threading.Thread(target=server)
            thread.start()
            ready.wait(1)
            self.assertEqual(request(path, "PING", timeout=0.05), "PONG")
            thread.join(1)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
