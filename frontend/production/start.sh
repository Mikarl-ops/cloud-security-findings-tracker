#!/bin/sh
set -eu
umask 077
: "${APP_HOST:?Set the reviewed application hostname}"
case "$APP_HOST" in
  *[!a-z0-9.-]*|"127.0.0.1") echo "Invalid APP_HOST" >&2; exit 1 ;;
esac
if [ "${#APP_HOST}" -gt 253 ] || ! printf '%s' "$APP_HOST" | grep -Eq '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$'; then
  echo "Invalid APP_HOST" >&2
  exit 1
fi
sed "s/__APP_HOST__/$APP_HOST/g" /etc/tracker/nginx.conf.template > /tmp/nginx.conf
exec "$@"
