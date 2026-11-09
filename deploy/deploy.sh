#!/bin/sh
# Deploy a git ref on the EC2 instance: ./deploy/deploy.sh <git-ref>
# To roll back, run it again with the previously deployed ref.
set -eu
ref="${1:?usage: deploy.sh <git-ref>}"
cd "$HOME/career-platform"
git fetch --all --prune
git checkout --detach "$ref"
"$HOME/.local/bin/uv" sync --locked --no-dev
sudo systemctl restart career-platform
i=0
while [ "$i" -lt 30 ]; do
    if curl -fsS -o /dev/null http://127.0.0.1:8000/api/v1/health; then
        echo "deployed $(git rev-parse --short HEAD)"
        exit 0
    fi
    i=$((i + 1))
    sleep 2
done
echo "health check failed for $(git rev-parse --short HEAD); recent logs:" >&2
sudo journalctl -u career-platform -n 30 --no-pager >&2
exit 1
