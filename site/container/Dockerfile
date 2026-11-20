# Public nginx mainline-alpine multi-platform index verified against Docker Registry.
ARG FREEFLIGHT_SITE_BASE_IMAGE=nginxinc/nginx-unprivileged:mainline-alpine@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e
FROM ${FREEFLIGHT_SITE_BASE_IMAGE}
# Keep the signed Alpine security updates pinned until the base image includes them.
USER 0:0
RUN apk add --no-cache \
    brotli-libs=1.2.1-r0 \
    curl=8.23.0-r0 \
    libcurl=8.23.0-r0 \
    libexpat=2.10.0-r0 \
    libxslt=1.1.43-r4 \
    musl=1.2.6-r3 \
    musl-utils=1.2.6-r3 \
    zlib=1.4-r0
COPY site/container/nginx.conf /etc/nginx/nginx.conf
COPY bin/.local/site/ /usr/share/nginx/html/
USER 101:101
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
