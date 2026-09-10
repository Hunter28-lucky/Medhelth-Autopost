# PulsePublish Deployment & Hosting Guide
**Author & System Architect:** Krish Goswami  
**Project:** AI Medical & AI News Publisher  

PulsePublish is designed to run anywhere with zero hosting fees, from your local Mac/PC (offline or connected) to free cloud containers or dedicated servers.

---

## Option 1: Run Locally on Your Computer (Easiest & 100% Free)
You do not need to pay for hosting. You can run the entire dashboard and research pipeline directly on your laptop, generate drafts, and push them straight to your remote WordPress site with one click.

### On macOS:
1. Double-click the file `start.command` in the project root folder.
2. The terminal will launch the server and open `http://127.0.0.1:8081`.
3. Enter your developer key: `krish@dev2026`.
4. Go to **Settings** and set your live WordPress URL and API key.
5. You can now research and push drafts to WordPress anytime!

### In Terminal (Mac/Linux/Windows WSL):
```bash
./start.sh
```

---

## Option 2: 1-Command Docker Deployment (Recommended for VPS / Servers)
If you have a server with Docker installed, you can launch the complete system with one command:

```bash
docker compose up -d
```
- Exposes port `8081` (`http://your-server-ip:8081`).
- Preserves your database in `./backend/publisher.db` across reboots.
- Includes automatic background scheduler running every 6 hours.

To stop or restart:
```bash
docker compose down
docker compose restart
```

---

## Option 3: Free Cloud Hosting (Railway / Render / Fly.io)

### Deploying to Render.com (Free Tier):
1. Push this project to your GitHub account (private repo).
2. Go to [Render.com](https://render.com) and create a **New Web Service**.
3. Select your GitHub repository.
4. Set the following:
   - **Environment:** `Docker`
   - **Dockerfile Path:** `./Dockerfile`
   - **Port:** `8081`
5. Add Environment Variables:
   - `DEVELOPER_PASSWORD`: `your-secure-password`
   - `OPENROUTER_API_KEY`: `your-openrouter-key`
   - `SEARCH_PROVIDER`: `free_online`
   - `WORDPRESS_URL`: `https://your-wordpress-site.com`
   - `WORDPRESS_API_KEY`: `your-wordpress-secret-key`
6. Click **Create Web Service**. Render will automatically build the React dashboard and Python backend into a live URL (e.g. `https://pulsepublish.onrender.com`).

### Deploying to Railway.app:
1. Open [Railway.app](https://railway.app) &rarr; **New Project** &rarr; **Deploy from GitHub repo**.
2. Railway detects the `Dockerfile` and builds automatically.
3. In Railway settings, add a volume pointing to `/app/backend` to keep your SQLite database persistent.
4. Generate a public domain.

---

## Option 4: Linux VPS (Ubuntu 22.04 / 24.04 with Systemd)
If you want to run it as a standing Linux background service:

1. Copy the project to your server:
   ```bash
   cd /var/www/pulsepublish
   ```
2. Create virtual environment & build frontend:
   ```bash
   python3 -m venv backend/venv
   ./backend/venv/bin/pip install -r backend/requirements.txt
   cd frontend && npm install && npm run build && cd ..
   ```
3. Create a systemd service `/etc/systemd/system/pulsepublish.service`:
   ```ini
   [Unit]
   Description=PulsePublish AI News Publisher
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/var/www/pulsepublish
   Environment="PYTHONPATH=/var/www/pulsepublish"
   ExecStart=/var/www/pulsepublish/backend/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8081
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
4. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pulsepublish
   sudo systemctl start pulsepublish
   ```

---

## WordPress Connection Setup
1. Download the **Pulse Content Sync** plugin zip from your dashboard (**Settings &rarr; Download .ZIP**) or at [ai-news-publisher.zip](file:///Users/krishyogi/Desktop/web%20post/wp-plugin/ai-news-publisher.zip).
2. In your WordPress Admin:
   - Go to **Plugins &rarr; Add New Plugin &rarr; Upload Plugin**.
   - Choose `ai-news-publisher.zip` and click **Install Now** &rarr; **Activate Plugin**.
3. Go to **Settings &rarr; Pulse Content Sync**:
   - Copy the generated 32-character API Key.
4. Back in the PulsePublish Dashboard:
   - Go to **Settings &rarr; WordPress Integration**.
   - Paste your WordPress URL and API key.
   - Click **Test WP Connection** &rarr; Verify green checkmark.
5. All generated drafts will now sync directly as native WordPress drafts with full Yoast SEO v28.4 compliance!
