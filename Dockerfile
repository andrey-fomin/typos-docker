# syntax=docker/dockerfile:1.7

FROM python:3.13-alpine AS fetcher
ARG TYPOS_VERSION
ARG TARGETARCH=amd64
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /work
RUN apk add --no-cache ca-certificates
COPY scripts/typos_release.py ./scripts/typos_release.py
RUN test -n "$TYPOS_VERSION"
RUN python3 ./scripts/typos_release.py fetch --version "$TYPOS_VERSION" --arch "$TARGETARCH" --output-dir /out
RUN apk add --no-cache file && file /out/typos | grep -Eq 'statically linked|static-pie linked'

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=fetcher /out/typos /usr/local/bin/typos
COPY licenses/upstream/ /licenses/
ENTRYPOINT ["/usr/local/bin/typos"]
CMD ["--help"]
