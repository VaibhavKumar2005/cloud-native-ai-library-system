# Build Stage
FROM node:20-alpine3.19 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production Stage
FROM nginx:1.25-alpine3.18-slim

# SECURITY REMEDIATION:
# Fixes CVE-2023-45322 (libxml2), CVE-2022-43680 (libexpat), 
# CVE-2023-5363 (openssl), and busybox/musl vulnerabilities
RUN apk update && \
    apk upgrade --no-cache && \
    rm -rf /var/cache/apk/*

COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]