from __future__ import annotations

import socket
import tempfile
import threading
import unittest
from pathlib import Path

from amiga_emulator.ipc import request


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


if __name__ == "__main__":
    unittest.main()
