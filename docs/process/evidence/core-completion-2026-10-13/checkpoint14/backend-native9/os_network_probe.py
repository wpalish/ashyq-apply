"""Root-reviewed negative inherited OS probe; no app/provider imports or DNS."""
from __future__ import annotations

import errno
import json
import socket
import subprocess
import sys
from pathlib import Path


def checks() -> list[dict]:
    rows = []
    for action in ('bind', 'connect', 'sendto'):
        for family, address in ((socket.AF_INET, ('127.0.0.1', 9)), (socket.AF_INET6, ('::1', 9))):
            socktype = socket.SOCK_DGRAM if action == 'sendto' else socket.SOCK_STREAM
            with socket.socket(family, socktype) as sock:
                sock.settimeout(1)
                try:
                    if action == 'sendto':
                        sock.sendto(b'synthetic sandbox negative probe', address)
                    else:
                        getattr(sock, action)(address if action == 'connect' else (address[0], 0))
                except OSError as exc:
                    denied = exc.errno in (errno.EPERM, errno.EACCES)
                    rows.append({'family': family.name, 'action': action, 'denied_by_os': denied, 'errno': exc.errno})
                else:
                    rows.append({'family': family.name, 'action': action, 'denied_by_os': False})
            if not rows[-1]['denied_by_os']:
                return rows  # stop on first unexpected permission/result
    return rows


output = Path(sys.argv[1])
rows = checks()
passed = len(rows) == 6 and all(row['denied_by_os'] for row in rows)
result = {'passed': passed, 'checks': rows, 'scope': 'OS transport refusal; no current research/quality probe'}
if '--child' not in sys.argv and passed:
    child_output = output.with_name('os-network-child-probe.json')
    # A real Bash descendant execs Python -I without our sitecustomize guard.
    # This measures kernel sandbox inheritance, not Python monkeypatch behavior.
    child = subprocess.run(['/bin/bash', '-c', 'exec "$1" -I "$2" "$3" --child',
                            'synthetic-probe', sys.executable, str(Path(__file__).resolve()), str(child_output)],
                           capture_output=True, timeout=10, check=False)
    child_result = json.loads(child_output.read_text()) if child_output.exists() else {'passed': False}
    result['descendant'] = child_result
    result['descendant_exit_code'] = child.returncode
    result['passed'] = passed and child.returncode == 0 and child_result.get('passed') is True
    result['scope'] = 'Sandboxed Python parent plus actual Bash/Python -I descendant transport refusal'
output.write_text(json.dumps(result, indent=2) + '\n')
raise SystemExit(0 if result['passed'] else 2)
