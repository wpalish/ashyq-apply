const fs = require('node:fs');
const net = require('node:net');
const tls = require('node:tls');
const http = require('node:http');
const https = require('node:https');
const dgram = require('node:dgram');
const dns = require('node:dns');
let attempts = 0;
const denied = () => { attempts++; throw new Error('A_PEER_NETWORK_DENIED'); };
net.Socket.prototype.connect = denied;
net.Server.prototype.listen = denied;
tls.connect = denied;
http.request = http.get = https.request = https.get = denied;
dgram.createSocket = denied;
for (const key of ['lookup','resolve','resolve4','resolve6','reverse']) { dns[key] = denied; if (dns.promises) dns.promises[key] = async () => denied(); }
globalThis.fetch = denied;
process.on('exit', () => { if (process.env.REVIEW_NETWORK_LOG_DIR) fs.writeFileSync(`${process.env.REVIEW_NETWORK_LOG_DIR}/network-${process.pid}.json`, JSON.stringify({pid:process.pid, attempts})+'\n'); });
