# typos Docker image

[![CI](https://github.com/andrey-fomin/typos-docker/actions/workflows/ci.yml/badge.svg)](https://github.com/andrey-fomin/typos-docker/actions/workflows/ci.yml)
[![Publish](https://github.com/andrey-fomin/typos-docker/actions/workflows/publish.yml/badge.svg)](https://github.com/andrey-fomin/typos-docker/actions/workflows/publish.yml)
[![Docker Image Version](https://img.shields.io/docker/v/andreyfomin/typos?sort=semver)](https://hub.docker.com/r/andreyfomin/typos)

Run [`crate-ci/typos`](https://github.com/crate-ci/typos) with Docker, without installing the binary on your machine.

Docker Hub: [`andreyfomin/typos`](https://hub.docker.com/r/andreyfomin/typos)

## Quick start

Show help:

```console
docker run --rm andreyfomin/typos --help
```

Check the current directory:

```console
docker run --rm -v "$PWD:/work" -w /work andreyfomin/typos
```

Check a specific file or path:

```console
docker run --rm -v "$PWD:/work" -w /work andreyfomin/typos README.md src/
```

## Common usage

Write fixes back to files:

```console
docker run --rm -v "$PWD:/work" -w /work --user "$(id -u):$(id -g)" andreyfomin/typos --write-changes
```

Show a diff instead of changing files:

```console
docker run --rm -v "$PWD:/work" -w /work andreyfomin/typos --diff
```

Use a custom config file:

```console
docker run --rm -v "$PWD:/work" -w /work andreyfomin/typos --config .typos.toml
```

Read from stdin:

```console
printf 'mispeling' | docker run --rm -i andreyfomin/typos -
```

## Tags

- `latest`: latest stable upstream `typos` release
- `1`: latest stable release in major version 1
- `1.44`: latest stable release in minor series 1.44
- `1.44.0`: exact upstream version

Docker tags drop the upstream `v` prefix.

## Image details

- entrypoint is `typos`, so you pass normal CLI arguments directly
- runs as `nonroot` by default
- publishes `linux/amd64` and `linux/arm64`
- packages the official upstream musl release binaries
- includes upstream license texts in `/licenses`

## File permissions

The image runs as a non-root user. That is usually fine for read-only scans.

If you use `--write-changes` with a bind mount, prefer:

```console
--user "$(id -u):$(id -g)"
```

This avoids permission problems and unexpected file ownership on the host.

## Updates

This image tracks stable upstream `typos` releases automatically. The publish workflow checks for new releases every 6 hours and pushes updated Docker tags when a new stable version appears.

## Upstream

- project: `https://github.com/crate-ci/typos`
- license: `MIT OR Apache-2.0`

## For maintainers

Publishing is handled by `.github/workflows/publish.yml`.

Required GitHub repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
