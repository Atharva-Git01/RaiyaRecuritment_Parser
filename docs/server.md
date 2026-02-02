t
# 🚀 Ultimate Deployment Guide for Hostinger VPS
**Project: Resume Experience Platform**  
**OS: Ubuntu 22.04 / 24.04 LTS**

Welcome! This guide is written for a "first-timer," assuming you have a fresh VPS from Hostinger and a domain name. We will set up a professional, production-grade environment.

---

## ✅ Phase 1: Prerequisites
1.  **Hostinger VPS**: Choose the "KVM 1" or higher plan (at least 4GB RAM is recommended because we are running AI models like `sentence-transformers` and `Phi-4` API calls).
2.  **Domain Name**: Buy a domain (e.g., `myresumetool.com`) and point its **A Record** to your VPS IP Address in the DNS settings.

---

## 🔑 Phase 2: Connecting to Your Server
You received an IP address (e.g., `123.45.67.89`) and a root password from Hostinger.

1.  Open your terminal (Command Prompt/PowerShell on Windows).
2.  Run the SSH command:
    ```bash
    ssh root@<your-vps-ip>
    ```
3.  Type `yes` if asked, then enter your password.

---

## 🛠 Phase 3: System Setup & Security
First, let's update the server and install essential tools.

```bash
# 1. Update system packages
apt update && apt upgrade -y

# 2. Install Python, Git, Nginx, and MySQL
apt install python3-pip python3-venv git nginx mysql-server -y

# 3. Install build tools (needed for some python packages)
apt install build-essential libssl-dev libffi-dev python3-dev -y
```

---

## 📂 Phase 4: Setting Up the Application

### 1. Create a Project Directory
We will put our code in `/var/www/resume_app`.

```bash
mkdir -p /var/www/resume_app
cd /var/www/resume_app
```

### 2. Upload Your Code
*Option A (Git - Recommended):* Push your local code to GitHub, then:
```bash
git clone https://github.com/yourusername/your-repo-name .
```
*Option B (Manual):* Use FileZilla or `scp` to upload files from your local Desktop to `/var/www/resume_app`.

### 3. Setup Virtual Environment
This keeps your project libraries separate from the system.

```bash
# Create venv
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Needed for production server
```

### 4. Create .env File
Copy your local environment configurations.
```bash
nano .env
```
Paste your API keys and secrets inside. Press `Ctrl+O`, `Enter` to save, and `Ctrl+X` to exit.

---

## 🗄 Phase 5: Database Setup (MySQL)
Your app uses `mysql-connector-python`, so we need a real database.

```bash
# 1. Secure MySQL installation (Answer 'Y' to all security questions)
mysql_secure_installation

# 2. Login to MySQL
mysql -u root -p

# 3. Run these SQL commands inside the MySQL shell:
CREATE DATABASE saas_db;
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON saas_db.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```
*Update your `.env` file with these new database credentials!*

---

## 🤖 Phase 6: Run as a Background Service (Systemd)
We don't want the app to stop when you close the SSH window. We use **Systemd** to keep it running 24/7.

### 1. Create a Service File
```bash
nano /etc/systemd/system/resume_app.service
```

### 2. Paste the Configuration
Replace `User=root` with your username if you created one, otherwise `root` is fine for now.

```ini
[Unit]
Description=Gunicorn instance to serve Resume App
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/resume_app
Environment="PATH=/var/www/resume_app/venv/bin"
# Run Gunicorn with Uvicorn workers
ExecStart=/var/www/resume_app/venv/bin/gunicorn -w 3 -k uvicorn.workers.UvicornWorker server:app --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

### 3. Start the Service
```bash
systemctl start resume_app
systemctl enable resume_app
systemctl status resume_app  # Should see "Active: active (running)"
```

---

## 🌐 Phase 7: Configure Nginx (Reverse Proxy)
Nginx sits in front of your app, handling user traffic and SSL.

### 1. Create Nginx Config
```bash
nano /etc/nginx/sites-available/resume_app
```

### 2. Paste Configuration
Replace `yourdomain.com` with your actual domain.

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Better Large File Upload Support (for PDFs)
    client_max_body_size 10M;
}
```

### 3. Activate and Check
```bash
ln -s /etc/nginx/sites-available/resume_app /etc/nginx/sites-enabled/
nginx -t  # Should say "syntax is ok"
systemctl restart nginx
```

---

## 🔒 Phase 8: Add SSL (HTTPS)
Never run a web app without HTTPS!

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Generate Certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
Follow the prompts (Enter email, Agree to Terms). Certbot will automatically update your Nginx config.

---

## 🛡️ Phase 9: Essential Security Hardening (MUST DO)
To mitigate unauthorized access and brute-force attacks, perform these critical security patches.

### 1. Enable UFW Firewall
Block all incoming traffic except essential ports (SSH, HTTP, HTTPS).
```bash
apt install ufw -y
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
# Type 'y' to confirm
```
*Verification:* `ufw status` should show "Status: active".

### 2. Install Fail2Ban (Block Brute-force)
Fail2Ban monitors login attempts and bans IPs that fail password authentication too many times.
```bash
apt install fail2ban -y
systemctl start fail2ban
systemctl enable fail2ban
```
*It is now protecting SSH automatically.*

### 3. Automatic Security Updates
Ensure your server patches itself against critical vulnerabilities.
```bash
apt install unattended-upgrades -y
dpkg-reconfigure --priority=low unattended-upgrades
```
Select **"Yes"** in the popup to enable automatic upgrades.

---

## 🎉 Done!
Your application is live at **https://yourdomain.com**.

### 🛠 Troubleshooting / Maintenance

**View App Logs:**
```bash
journalctl -u resume_app -f
```

**Restart App (after code changes):**
```bash
systemctl restart resume_app
```

**Reload Nginx (after config changes):**
```bash
systemctl restart nginx
```
