import socket, subprocess
def denied(*args, **kwargs):
    raise AssertionError("B offline peer denies network/DNS/CLI/process")
socket.create_connection=denied
socket.getaddrinfo=denied
socket.socket.connect=denied
socket.socket.connect_ex=denied
subprocess.run=denied
subprocess.Popen=denied
