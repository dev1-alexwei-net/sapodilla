# Dockerfile for the NGINX front-end.
# Based on nginx:alpine for small image size.
# The ollama-mirror.conf is baked into the image at build time.

FROM nginx:1.27-alpine AS final

# Remove default conf
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config
COPY ollama-mirror.conf /etc/nginx/conf.d/ollama-mirror.conf

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
    CMD wget -q -O - http://localhost:8080/healthz || exit 1

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
