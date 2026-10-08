"""Network-denied native pytest subprocess, normal imports from isolated source."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

DENIED = []


def deny(*args, **kwargs):
    DENIED.append('network/DNS')
    raise AssertionError('DENIED_REAL_NETWORK_IN_NATIVE_TEST_REPLAY')


socket.getaddrinfo = deny
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
import httpx

httpx.HTTPTransport.handle_request = deny


async def async_deny(*args, **kwargs):
    return deny(*args, **kwargs)


httpx.AsyncHTTPTransport.handle_async_request = async_deny
import pytest

result = pytest.main(sys.argv[1:])
from app.adapters.search import retrieval
from app.pipeline import control, read_budget
from app.adapters.discovery import live_discovery

path = Path(os.environ['CONTROL_RUNTIME']) / 'pytest-native-imports.json'
path.write_text(json.dumps({'exit_code': int(result), 'denied_network_attempts': len(DENIED),
    'modules': {m.__name__: {'path': str(Path(m.__file__).resolve()),
                            'sha256': hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()}
                for m in (retrieval, control, read_budget, live_discovery)}}, indent=2)+'\n')
if DENIED:
    raise AssertionError('REPLAY_ATTEMPTED_REAL_NETWORK')
sys.exit(result)
