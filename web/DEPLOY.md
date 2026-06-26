# 部署文档 — Kairos / 墨鉴

把项目部署到一台 Linux 云服务器（以 Ubuntu 22.04+ 为例）。架构是
**单机 + Nginx 反向代理**：Nginx 负责 HTTPS、托管前端静态文件，并把
`/api` 转发给本机的 FastAPI（uvicorn）。后端用 SQLite 落库，LLM 走
DeepSeek（或任意 OpenAI 兼容服务）。

```
                       ┌────────────────────────── 云服务器 ──────────────────────────┐
   浏览器  ──HTTPS──▶  │  Nginx :443                                                  │
                       │   ├─ /            → 前端静态文件 (frontend/dist)             │
                       │   └─ /api/*       → 127.0.0.1:8010  (uvicorn / FastAPI)      │
                       │                         ├─ SQLite  (web/charts.db, WAL)      │
                       │                         └─ LLM API (DeepSeek，出站 HTTPS)    │
                       └──────────────────────────────────────────────────────────────┘
```

> 适用规模：个人 / 小流量。SQLite 足够；并发上来后再迁移 Postgres。

---

## 0. 前置要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | **3.13+** | `bazibase` 引擎要求 `requires-python >=3.13`，不能用 3.12 |
| Node.js | 20 LTS | 仅构建期需要，构建产物是纯静态文件 |
| Nginx | 任意稳定版 | 反向代理 + TLS |
| 一个域名 | — | 指向服务器公网 IP，用于签 HTTPS 证书 |
| DeepSeek API Key | — | 没有 Key 时后端会退化为「确定性回复」，但不调用 LLM |

把域名的 A 记录解析到服务器公网 IP，并放行安全组的 **80 / 443** 端口。

---

## 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y nginx git curl

# Python 3.13（Ubuntu 22.04 自带版本偏低，用 deadsnakes）
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.13 python3.13-venv

# Node 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

---

## 2. 拉取代码

建议放在 `/opt`：

```bash
sudo mkdir -p /opt && sudo chown "$USER" /opt
cd /opt
git clone <你的仓库地址> bazibase
cd bazibase
git checkout feat/session-redesign-agent-polish   # 或你要发布的分支
```

后文用 `APP=/opt/bazibase` 代指项目根目录。

---

## 3. 部署后端（FastAPI）

### 3.1 创建虚拟环境并安装依赖

```bash
cd /opt/bazibase
python3.13 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e .                       # 安装 bazibase 引擎 + lunar_python
pip install -r web/requirements.txt    # 安装 web 后端依赖
```

### 3.2 配置环境变量

后端从 `web/.env` 读取配置（`web/backend/config.py`）。**生产环境必改 3 项**：
`DEEPSEEK_API_KEY`、`JWT_SECRET`、`COOKIE_SECURE=true`。

```bash
cd /opt/bazibase/web
cp .env.example .env
# 生成一个强随机 JWT 密钥
echo "JWT_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

编辑 `web/.env`：

```ini
# ── 必填 ──
DEEPSEEK_API_KEY=sk-你的真实key
JWT_SECRET=上一步生成的64位十六进制串
COOKIE_SECURE=true          # 生产是 HTTPS，必须 true，否则登录 Cookie 不下发

# ── 可选 ──
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATABASE_PATH=charts.db     # 相对 web/ 目录，默认即可
JWT_EXPIRE_DAYS=30

# 换别的模型服务（任意 OpenAI 兼容 /chat/completions），填这三个即可覆盖 DeepSeek：
# LLM_BASE_URL=https://your-provider/v1
# LLM_API_KEY=sk-xxx
# LLM_MODEL=your-model
```

> `.env` 含密钥，**不要提交到仓库**。

### 3.3 手动验证一次

后端用了包内相对导入，**必须在 `web/` 目录下**以 `backend.main:app` 启动：

```bash
cd /opt/bazibase/web
../.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8010
# 另开终端：
curl -s http://127.0.0.1:8010/api/health    # 期望 {"status":"ok"}
```

确认无误后 `Ctrl-C`，下一步交给 systemd 托管。

### 3.4 配置 systemd 常驻服务

`sudo nano /etc/systemd/system/kairos.service`：

```ini
[Unit]
Description=Kairos FastAPI backend
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/bazibase/web
ExecStart=/opt/bazibase/.venv/bin/uvicorn backend.main:app \
          --host 127.0.0.1 --port 8010 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> SQLite 已开启 WAL，2 个 worker 没问题；若发现写入偶发 `database is locked`，
> 把 `--workers` 降为 1。要再高并发就该换 Postgres 了。

让 `www-data` 能读写代码目录和数据库：

```bash
sudo chown -R www-data:www-data /opt/bazibase/web
sudo systemctl daemon-reload
sudo systemctl enable --now kairos
sudo systemctl status kairos          # 看是否 active (running)
journalctl -u kairos -f               # 实时日志
```

---

## 4. 构建前端

前端 API 客户端用相对路径 `/api`（`web/frontend/src/api/client.ts`），所以
**只要前后端同源**（同一个 Nginx）就不需要配任何后端地址，也不会有跨域问题。

```bash
cd /opt/bazibase/web/frontend
npm ci
npm run build        # 产物输出到 web/frontend/dist
```

`dist/` 就是要交给 Nginx 托管的静态目录。

> `vite.config.ts` 里写死的 HMR host 只影响本地 `npm run dev`，对 `build` 无影响，
> 不用管。

---

## 5. 配置 Nginx

`sudo nano /etc/nginx/sites-available/kairos`：

```nginx
server {
    listen 80;
    server_name your-domain.com;          # 改成你的域名

    root /opt/bazibase/web/frontend/dist;
    index index.html;

    # 前端是 SPA：找不到的路径回退到 index.html（支持 /session/:id 这类前端路由）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反代到本机 uvicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # ⚠️ 聊天是流式 NDJSON（application/x-ndjson），必须关闭缓冲，
        #    否则回复会被 Nginx 攒着、不能逐字输出。
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header X-Accel-Buffering no;
        proxy_read_timeout 600s;          # 长回复留足时间
    }

    client_max_body_size 4m;
}
```

启用并重载：

```bash
sudo ln -s /etc/nginx/sites-available/kairos /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

此时用 `http://your-domain.com` 应该能打开站点。

---

## 6. 开启 HTTPS（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

certbot 会自动改写上面的 server 块、加上 443 与证书、并配置 80→443 跳转。
证书自动续期（`systemctl status certbot.timer` 可确认）。

完成后确认 `web/.env` 里 `COOKIE_SECURE=true`（HTTPS 下登录 Cookie 才会下发），
改过就 `sudo systemctl restart kairos`。

---

## 7. 数据库与备份

- 数据库是单文件 `web/charts.db`（WAL 模式，运行时会有 `charts.db-wal` / `-shm` 伴生文件）。
- 首次启动时 `init_db()` 自动建表，无需手动初始化。
- **重新部署 / 拉新代码不要删除 `charts.db`**，否则用户、会话、记忆全丢。
- 简单定时备份：

```bash
# 用 sqlite3 的在线备份，避免拷到写一半的文件
sudo apt install -y sqlite3
sqlite3 /opt/bazibase/web/charts.db ".backup '/opt/backups/charts-$(date +\%F).db'"
```

可丢进 crontab 每日跑一次。

---

## 8. 日常更新发布

```bash
cd /opt/bazibase
git pull

# 后端依赖有变化时：
source .venv/bin/activate
pip install -e . && pip install -r web/requirements.txt
sudo systemctl restart kairos

# 前端有变化时：
cd web/frontend && npm ci && npm run build      # dist 原地更新，Nginx 无需重启
```

> 数据库结构是「`CREATE TABLE IF NOT EXISTS`」式的幂等建表，新增表会在重启时
> 自动创建；但**已有表的字段变更不会自动迁移**，那种情况需要手写迁移脚本。

---

## 9. 排错速查

| 现象 | 排查方向 |
|------|----------|
| 打开站点 502 | 后端没起来：`systemctl status kairos`、`journalctl -u kairos -e` |
| 聊天回复「一次性蹦出来」而非逐字 | Nginx 没关缓冲：确认 `/api/` 块里有 `proxy_buffering off` |
| 登录后刷新又退出 / Cookie 不保存 | `COOKIE_SECURE` 与协议不匹配：HTTPS 必须 `true`，纯 HTTP 调试用 `false` |
| 回复内容很笼统、像没用 AI | `DEEPSEEK_API_KEY` 没配或额度/网络问题，后端退化为确定性回复；看后端日志 |
| 启动报 `ImportError: bazibase` | 没在 `web/` 目录启动，或没 `pip install -e .`（缺 lunar_python） |
| `database is locked` | 把 systemd 的 `--workers` 降到 1 |
| 前端刷新子路由 404 | Nginx 缺 SPA 回退：`try_files $uri $uri/ /index.html` |

---

## 附：前后端不同域名的情况

如果前端单独放在 CDN / 另一个域名（与后端不同源），需要额外处理：

1. 后端 `main.py` 的 CORS 目前是 `allow_origins=["*"]` 配 `allow_credentials=True`，
   浏览器会拒绝带 Cookie 的跨域请求——必须把 `allow_origins` 改成**明确的前端域名**列表。
2. 前端的 `/api` 相对路径要改成后端绝对地址（或在 CDN 层做 `/api` 反代）。

**推荐还是同源部署**（本文方案），省去以上所有麻烦。
