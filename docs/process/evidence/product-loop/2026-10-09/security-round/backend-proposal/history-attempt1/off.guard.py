import socket, os, json, atexit
ATTEMPTS=[]
def denied(*args, **kwargs):
    ATTEMPTS.append({"kind":"socket_or_dns","argument_types":[type(v).__name__ for v in args]})
    raise AssertionError("DENIED_REAL_NETWORK")
socket.socket.connect=denied
socket.socket.connect_ex=denied
socket.socket.bind=denied
socket.getaddrinfo=denied
socket.create_connection=denied
@atexit.register
def save():
    with open(os.environ["AUDIT_NETWORK_LOG"],"w") as f:
        json.dump({"attempts":ATTEMPTS,"count":len(ATTEMPTS)},f)
