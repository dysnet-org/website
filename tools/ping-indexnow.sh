#!/bin/sh
# Tell the IndexNow engines (Bing, Yandex, Seznam) that the site has changed.
# Run it after a deploy has gone live; the key file it points at is written by build-demo.py.
# Usage: sh tools/ping-indexnow.sh
set -e
KEY=f1faf0b594023c386c5540e7b7fad1a0
HOST=www.dysnet.org
URLS=$(curl -s "https://$HOST/sitemap.xml" | sed -n 's:.*<loc>\(.*\)</loc>.*:\1:p' | sed 's/.*/"&"/' | paste -sd, -)
curl -sS -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{\"host\":\"$HOST\",\"key\":\"$KEY\",\"keyLocation\":\"https://$HOST/$KEY.txt\",\"urlList\":[$URLS]}" \
  -w "\nIndexNow: HTTP %{http_code}\n"
