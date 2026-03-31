FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /docs

# Pin mkdocs AND mkdocs-material explicitly to prevent MkDocs 2.0 being
# pulled in as a transitive dependency
RUN pip install --no-cache-dir \
    "mkdocs==1.6.1" \
    "mkdocs-material>=9.5,<10" \
    mkdocs-minify-plugin \
    mkdocs-redirects \
    mkdocs-glightbox \
    mkdocs-section-index \
    mkdocs-macros-plugin \
    mkdocs-autorefs \
    mkdocs-include-markdown-plugin \
    mkdocs-table-reader-plugin \
    mkdocs-swagger-ui-tag \
    mkdocstrings[python] \
    pillow

COPY docs/ docs/
COPY mkdocs.yml .

RUN mkdocs build

FROM nginx:alpine
RUN apk add --no-cache wget
COPY --from=builder /docs/site /usr/share/nginx/html
RUN printf 'server {\n    listen 8000;\n    root /usr/share/nginx/html;\n    index index.html;\n    location / { try_files $uri $uri/ $uri/index.html =404; }\n}\n' \
    > /etc/nginx/conf.d/mkdocs.conf && rm /etc/nginx/conf.d/default.conf
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=5 \
    CMD wget -qO- http://localhost:8000/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
