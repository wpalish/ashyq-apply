const fs = require('node:fs');
const path = require('node:path');
const { syncBuiltinESMExports } = require('node:module');
const counts = { dns: 0, socket: 0, listen: 0, request: 0 };
const ownedGuardDir = process.env.OWNED_GUARD_DIR;
const ownedGuardPhase = process.env.OWNED_GUARD_PHASE;
const deny = (kind) => function () { counts[kind]++; throw new Error(`OWNED_OFFLINE_GUARD:${kind}`); };
const net = require('node:net');
const tls = require('node:tls');
const dns = require('node:dns');
const http = require('node:http');
const https = require('node:https');
net.Socket.prototype.connect = deny('socket');
net.connect = deny('socket'); net.createConnection = deny('socket');
net.Server.prototype.listen = deny('listen');
tls.connect = deny('socket');
for (const mod of [http, https]) { mod.request = deny('request'); mod.get = deny('request'); }
for (const name of ['lookup', 'lookupService', 'resolve', 'resolve4', 'resolve6', 'resolveAny', 'resolveCname', 'resolveMx', 'resolveNaptr', 'resolveNs', 'resolvePtr', 'resolveSoa', 'resolveSrv', 'resolveTxt', 'reverse']) {
  if (typeof dns[name] === 'function') dns[name] = deny('dns');
  if (typeof dns.promises[name] === 'function') dns.promises[name] = deny('dns');
}
globalThis.fetch = deny('request');
syncBuiltinESMExports();
function flush(suffix = 'exit') {
  if (!ownedGuardDir || !ownedGuardPhase) throw new Error('Owned guard env required');
  const item = { pid: process.pid, phase: ownedGuardPhase, suffix, counts };
  fs.writeFileSync(path.join(ownedGuardDir, `guard-${ownedGuardPhase}-${process.pid}-${suffix}.json`), `${JSON.stringify(item)}\n`);
}
module.exports = { counts, flush };
process.on('exit', () => flush());
