# Pi-hole

The only file in this folder that is committed is
[`docker-compose.yml`](docker-compose.yml). Everything else
(`etc-pihole/`, `etc-dnsmasq.d/`, `logs/`) is **runtime state** created by
the container on first start and is git-ignored.

The `.gitkeep` markers exist only to make sure those host directories are
present on a fresh clone so Docker's bind mounts succeed.

## Why a non-default port?

The host DNS port is **5354** (not 53). Windows already binds 53 in many
environments and we want a reproducible setup that won't conflict with the
host resolver. All scripted traffic targets `127.0.0.1:5354`.

## Admin web UI

Available at <http://localhost:8081> while the container is running.
Default password is set in `docker-compose.yml` (`WEBPASSWORD: admin12345`)
for development convenience — change this if you ever expose the container.
