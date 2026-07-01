#!/usr/bin/env bash
# 一键更新 Kairos（在服务器上以 root 跑）：
#   拉最新代码 → 更新后端依赖 → 重建前端 → 刷新静态 → 重启后端 → 重载 Caddy
# 用法：bash /root/kairos/deploy/update.sh
set -euo pipefail

REPO=/root/kairos
STATIC=/var/www/kairos
VENV="$REPO/web/.venv"

cd "$REPO"

echo "==> 1/5 拉取最新代码（当前分支）"
git pull --ff-only

echo "==> 2/5 更新后端依赖"
"$VENV/bin/pip" install -e . -q
"$VENV/bin/pip" install -r web/requirements.txt -q

echo "==> 3/5 构建前端"
cd web/frontend
npm install --no-audit --no-fund --silent
npm run build

echo "==> 4/5 刷新静态到 $STATIC"
mkdir -p "$STATIC"
rm -rf "${STATIC:?}"/*
cp -r dist/. "$STATIC"/
chmod -R a+rX "$STATIC"

echo "==> 5/5 重启后端 + 重载 Caddy"
systemctl restart kairos
systemctl reload caddy

echo "==> 健康检查"
sleep 2
curl -s http://127.0.0.1:8010/api/health && echo
echo "✓ 更新完成"
