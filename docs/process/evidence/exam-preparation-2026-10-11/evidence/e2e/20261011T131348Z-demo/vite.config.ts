import native from "/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend/vite.config.ts";
export default { ...native,
 cacheDir: "/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/exam-preparation-2026-10-11/evidence/e2e/20261011T131348Z-demo/vite-cache",
 server: {...native.server,host:"127.0.0.1",port:5229,strictPort:true,
 proxy:{"/api":{target:"http://127.0.0.1:8139",changeOrigin:true}}},
};
