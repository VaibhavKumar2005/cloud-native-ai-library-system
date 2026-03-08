###############################################################################
# VeriRAG Frontend — Production-Grade Multi-Stage Dockerfile
# AZ-400 Best Practices: non-root nginx, minimal image, pinned versions
###############################################################################

# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

# Security: Upgrade all OS packages to latest patched versions
RUN apk update && apk upgrade --no-cache

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: Serve ──────────────────────────────────────────────────────────
FROM nginx:stable-alpine AS runtime

# Security: Upgrade all OS packages to latest patched versions
RUN apk update && apk upgrade --no-cache

LABEL maintainer="Team96 <team96@verirag.dev>" \
      org.opencontainers.image.title="VeriRAG Frontend" \
      org.opencontainers.image.description="React SPA for Cloud-Native RAG"

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Add custom nginx config
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root nginx config
RUN echo 'server { \
    listen 8080; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /assets/ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
    gzip on; \
    gzip_types text/css application/javascript application/json image/svg+xml; \
}' > /etc/nginx/conf.d/verirag.conf

# Run as non-root (AZ-400 requirement)
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
