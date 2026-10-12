import native from "/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source/frontend/vite.config.ts";
export default { ...native,
 cacheDir: "/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/evidence/e2e/20261012T051801Z-auth/vite-cache",
 server: {...native.server,host:"127.0.0.1",port:5229,strictPort:true,
 fs:{...native.server?.fs,allow:[...(native.server?.fs?.allow ?? []),"/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source/frontend","/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend/node_modules/@fontsource/inter","/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend/node_modules/@fontsource/jetbrains-mono"]},
 proxy:{"/api":{target:"http://127.0.0.1:8139",changeOrigin:true}}},
};
