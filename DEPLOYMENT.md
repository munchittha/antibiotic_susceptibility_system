# Deploying the Website

This project is a Flask website. The production entry point is:

```text
wsgi.py
```

The Gunicorn command is:

```bash
gunicorn --bind 0.0.0.0:${PORT:-10000} wsgi:app
```

## Render

1. Push this project to GitHub.
2. Create a new Web Service on Render.
3. Connect the GitHub repository.
4. Use these settings:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn --bind 0.0.0.0:$PORT wsgi:app
```

Environment variables:

```text
SECRET_KEY = any long random string
SYSTEM_PIN = 1234
DATABASE_FILE = optional path for SQLite, for example /var/data/antibiotic_system.sqlite
```

The included `render.yaml` can also be used as a blueprint. Render will provide
the `PORT` environment variable automatically.

## Push to GitHub

From this project folder:

```bash
git init
git add .
git commit -m "Prepare Flask app for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace `YOUR-USERNAME` and `YOUR-REPOSITORY` with your GitHub account and
repository name.

## Deploy on Render

1. Go to https://dashboard.render.com/.
2. Choose **New** > **Web Service**.
3. Connect GitHub and select this repository.
4. Set **Language** to `Python 3`.
5. Set **Build Command** to `pip install -r requirements.txt`.
6. Set **Start Command** to `gunicorn --bind 0.0.0.0:$PORT wsgi:app`.
7. Add environment variables:

```text
SECRET_KEY = a long random secret value
SYSTEM_PIN = your staff PIN
```

8. Click **Create Web Service**.
9. When the build finishes, Render will show the public `onrender.com` URL.

Optional: if you add a Render persistent disk mounted at `/var/data`, also set:

```text
DATABASE_FILE = /var/data/antibiotic_system.sqlite
```

## Important Notes

- The current database is SQLite. This is fine for demo/local use.
- Some hosting platforms use temporary storage, so SQLite data may reset after redeploys.
- For a real multi-user deployment, move the database to PostgreSQL and replace the simple PIN with proper user accounts.
