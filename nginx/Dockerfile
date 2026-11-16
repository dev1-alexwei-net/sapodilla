# Dockerfile for the NGINX front-end.
# Based on nginx:alpine for small image size.
# The ollama-mirror.conf is baked into the image at build time.

FROM nginx:1.27-alpine AS final

# Remove default conf
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config as a template. The nginx:alpine entrypoint runs
# envsubst on files in /etc/nginx/templates/ and writes the result
# to /etc/nginx/conf.d/ — this lets us use $UPSTREAM from the
# environment without nginx's (unsupported) variable syntax in
# upstream blocks.
COPY ollama-mirror.conf /etc/nginx/templates/ollama-mirror.conf.template

# Restrict envsubst to only substitute $UPSTREAM so nginx
# variables like $host, $remote_addr are left intact.
ENV NGINX_ENVSUBST_FILTER='UPSTREAM'

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
    CMD wget -q -O - http://localhost:8080/healthz || exit 1

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
