const net = require('node:net');
const tls = require('node:tls');
const dgram = require('node:dgram');
const http = require('node:http');
const https = require('node:https');
const fs = require('node:fs');
let attempts = 0;
const forbidden = () => { attempts++; throw new Error('EXTERNAL_REVIEW_NETWORK_DENIED'); };
net.Socket.prototype.connect = forbidden;
net.Server.prototype.listen = forbidden;
tls.connect = forbidden;
dgram.createSocket = forbidden;
http.request = http.get = https.request = https.get = forbidden;
globalThis.fetch = forbidden;
process.on('exit', () => {
  if (process.env.REVIEW_NETWORK_LOG_DIR) fs.writeFileSync(`${process.env.REVIEW_NETWORK_LOG_DIR}/network-${process.pid}.json`, JSON.stringify({ pid: process.pid, network_or_listen_attempts: attempts }) + '\n');
});
