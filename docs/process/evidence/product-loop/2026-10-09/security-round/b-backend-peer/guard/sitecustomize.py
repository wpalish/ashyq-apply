import socket, os, json, atexit, traceback, sys
ATTEMPTS=[]
def deny(kind):
    def denied(*args, **kwargs):
        sock=args[0] if args else None
        peer=args[1] if len(args)>1 else None
        ATTEMPTS.append({"kind":kind,"family":int(sock.family) if isinstance(sock,socket.socket) else None,"target_loopback":bool(isinstance(peer,tuple) and peer and peer[0] in ("::1","127.0.0.1","localhost")),"port":peer[1] if isinstance(peer,tuple) and len(peer)>1 and type(peer[1]) is int else None,"stack":[{"file":f.filename,"line":f.lineno,"function":f.name} for f in traceback.extract_stack(limit=8)[:-1]]})
        raise AssertionError("DENIED_REAL_NETWORK")
    return denied
socket.socket.connect=deny("connect")
socket.socket.connect_ex=deny("connect_ex")
socket.socket.bind=deny("bind")
socket.getaddrinfo=deny("dns")
socket.create_connection=deny("create_connection")
@atexit.register
def save():
    with open(os.environ["AUDIT_NETWORK_LOG"],"w") as f:
        json.dump({"attempts":ATTEMPTS,"count":len(ATTEMPTS),"app_module_origins":{k:getattr(v,"__file__",None) for k,v in sys.modules.items() if k in ("app.config","app.main","app.api.routes_social","app.security","app.db")}},f,indent=2)
