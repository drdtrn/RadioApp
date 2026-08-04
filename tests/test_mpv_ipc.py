import json
import socket
import threading

from radio_tui.mpv_ipc import MPVIPCClient


def test_send_command_returns_response_and_captures_events():
    client_sock, server_sock = socket.socketpair()
    client = MPVIPCClient(client_sock)

    def fake_mpv():
        server_sock.recv(4096)  # consume the command the client sent
        server_sock.sendall(json.dumps({"event": "idle"}).encode() + b"\n")
        server_sock.sendall(json.dumps({"error": "success", "data": None}).encode() + b"\n")

    thread = threading.Thread(target=fake_mpv)
    thread.start()

    response = client.send_command(["loadfile", "http://example/stream"])
    thread.join()

    assert response == {"error": "success", "data": None}
    assert list(client.events) == [{"event": "idle"}]

    client.close()
    server_sock.close()


def test_send_command_raises_when_socket_closes_before_response():
    client_sock, server_sock = socket.socketpair()
    client = MPVIPCClient(client_sock)
    server_sock.close()

    try:
        client.send_command(["get_property", "volume"])
        assert False, "expected ConnectionError"
    except ConnectionError:
        pass

    client.close()
