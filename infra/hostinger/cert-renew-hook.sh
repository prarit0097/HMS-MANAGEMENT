#!/bin/sh
set -eu
case " ${RENEWED_DOMAINS:-} " in
  *" hms.praritsidana.com "*) /usr/sbin/nginx -t && /bin/systemctl reload nginx ;;
esac
