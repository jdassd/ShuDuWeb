# ShuDuWeb
网页双人对战数独游戏

## 开发运行

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:asgi_app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认后端地址为 `http://localhost:8000`，前端使用 `VITE_API_BASE` 和 `VITE_SOCKET_BASE` 可切换。

## Docker 运行

```bash
docker build -t shuduweb .
docker run --rm -p 8000:8000 shuduweb
```

浏览器访问 `http://localhost:8000`。
