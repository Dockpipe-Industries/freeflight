# Public nginx stable-alpine multi-platform index verified against Docker Registry.
ARG FREEFLIGHT_SITE_BASE_IMAGE=nginxinc/nginx-unprivileged:stable-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03
FROM ${FREEFLIGHT_SITE_BASE_IMAGE}
COPY site/container/nginx.conf /etc/nginx/nginx.conf
COPY bin/.local/site/ /usr/share/nginx/html/
USER 101:101
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
