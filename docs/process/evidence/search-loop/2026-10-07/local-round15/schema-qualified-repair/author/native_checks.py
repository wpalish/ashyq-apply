from pathlib import Path
import socket
import sys

def denied(*_args, **_kwargs):
    raise AssertionError('Real socket/DNS forbidden in offline schema control')

socket.socket.connect = denied
socket.socket.connect_ex = denied
socket.create_connection = denied
socket.getaddrinfo = denied
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
