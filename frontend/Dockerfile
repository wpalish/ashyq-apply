# ASHYQ Apply — frontend, built once and served as static files by nginx.

FROM node:22-bookworm-slim AS builder

WORKDIR /build

# npm ci installs exactly the lockfile, so a build is reproducible.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# The unprivileged image already runs as uid 101 and listens on 8080.
COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
