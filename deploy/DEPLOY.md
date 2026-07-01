# 部署手册 — Kairos（单台美西/美东服务器 · 无域名 · DuckDNS + Caddy 自动 HTTPS）

架构：`浏览器 ──HTTPS──> Caddy ──┬─ /        前端静态(web/frontend/dist)`
`                                └─ /api/*   反代 → uvicorn 127.0.0.1:8010 (FastAPI)`

同源部署 → 不用配 CORS，cookie 天然能带。后端绑 127.0.0.1（只有 Caddy 能碰，不对公网暴露）。

假设：Ubuntu 22.04+，已开放 **80/443** 端口，有 sudo。把 `<REPO>` 换成你 clone 的路径，`<SUB>` 换成你的 DuckDNS 子域名。

---

## ⚠️ 0. 先解决 LLM 延迟（美西/美东必做）

DeepSeek 在国内，你服务器在美国，每次咨询要**串行 3–6 次 LLM 调用**，全跨太平洋 → 慢。
**把 LLM 换成美国托管、说 OpenAI 协议的**（只改 `.env`，不动代码）：

- **Together** `https://api.together.xyz/v1`（可跑 `deepseek-ai/DeepSeek-V3`，质量接近、在美）
- **Groq** `https://api.groq.com/openai/v1`（极快）
- **Fireworks** / **OpenAI** 亦可

换完**必须跑 eval 确认质量没掉**（见第 7 步）。

---

## 1. DuckDNS（免费子域名 → Caddy 才能自动签证书）

1. 上 https://www.duckdns.org 用 GitHub/Google 登录，建一个 `<SUB>`（如 `kairos-xyz`）。
2. 把它的 IP 指到你**服务器公网 IP**（页面上填，或之后用它给的 token + cron 自动更新）。
3. 验证：`dig +short <SUB>.duckdns.org` 应返回你的服务器 IP。

## 2. 装系统依赖

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nodejs npm git
# 装 Caddy（官方源）
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

## 3. 拉代码 + 装后端

```bash
git clone <你的仓库> <REPO> && cd <REPO>
python3 -m venv web/.venv
web/.venv/bin/pip install --upgrade pip
web/.venv/bin/pip install -e .                      # bazibase + 其依赖(lunar_python 等)
web/.venv/bin/pip install -r web/requirements.txt   # fastapi / uvicorn 等后端依赖
```

## 4. 生产 `.env`（放在 `web/.env`）

```bash
cp deploy/env.production.example web/.env
# 生成强密钥并填进去：
openssl rand -hex 32      # 复制到 JWT_SECRET
nano web/.env             # 填 JWT_SECRET、LLM_*（用第 0 步的美国供应商）、确认 COOKIE_SECURE=true
```

## 5. 构建前端

```bash
cd web/frontend && npm ci && npm run build && cd ../..
# 产物在 web/frontend/dist
# 确认前端调用的是相对路径 /api（与 dev 的 proxy 一致）→ 同源即可，无需额外配置
```

## 6. 后端进程（systemd 守护）

```bash
# 编辑 deploy/kairos.service 里的 <REPO> 路径，然后：
sudo cp deploy/kairos.service /etc/systemd/system/kairos.service
sudo systemctl daemon-reload
sudo systemctl enable --now kairos
sudo systemctl status kairos          # 看是否 running
curl -s http://127.0.0.1:8010/api/health   # 应返回 {"status":"ok"}
```

## 7. ⭐ 上线前跑 eval（确认换的美国模型质量没掉）

```bash
cd <REPO> && PYTHONPATH=. web/.venv/bin/python -m web.backend.eval.run
# 看「忠于引擎事实 / grounding / 总分」对比之前 DeepSeek 的基线(~4.6)有没有明显下滑
# 掉了就微调 responder prompt 再跑，直到新模型也稳
```

## 8. Caddy（自动 HTTPS + 同源反代）

```bash
# 编辑 deploy/Caddyfile：把 <SUB> 和 <REPO> 换成你的实际值
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
# Caddy 会自动向 Let's Encrypt 申请 <SUB>.duckdns.org 的证书并续期
```

打开 `https://<SUB>.duckdns.org` —— 应能看到应用，且是绿锁 HTTPS。

---

## 上线前的产品决定

- **登录闸**：本地调试时把引导登录注释掉了。线上决定开/关；要开就确认 `COOKIE_SECURE=true`（已在 .env）。
- **数据库**：SQLite 文件（默认在 `web/` 下，`*.db`）。低流量够用，但要：① 放在持久路径 ② **定期备份**（`cron` + `cp`/`sqlite3 .backup`）。
- **CORS**：同源部署用不到；`main.py` 里 `allow_origins=["*"]` 同源下不生效、无害，但建议日后删掉或收成具体域名。
- **worker 数**：先用 **1 个**（SQLite 写 + 进程内缓存，单 worker 最省事；应用是 I/O 密集、靠 async/线程池并发，低流量足够）。要扩再说。

## 日常运维

```bash
sudo systemctl restart kairos     # 改后端代码后
sudo journalctl -u kairos -f      # 看后端日志
# 更新代码：git pull → 重装依赖(如有变) → npm run build → systemctl restart kairos → reload caddy
```
