# Portfolio Website (FastAPI)

Personal portfolio web app built with **FastAPI**, **Jinja2 templates**, **PostgreSQL**, and vanilla **JavaScript/CSS**.

## Features

- Multi-page portfolio: About, Resume, Blog, Contact, Daily Routine
- Admin authentication (cookie-based session)
- Admin settings: update username/password
- Blog CRUD (create, read, update, delete)
- Daily routine posts + replies
- Contact form (SMTP email)
- PostgreSQL-backed storage
- Timezone-aware timestamp handling (UTC storage, local display)

## Tech Stack

- Python
- FastAPI
- Jinja2
- PostgreSQL (`psycopg2`)
- HTML/CSS/JavaScript

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── templates/
├── static/
└── PROJECT_STRUCTURE.md
```

## Run Locally

1. Clone the repo
2. Create and activate virtual environment
3. Install dependencies
4. Set environment variables
5. Start server

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes (prod) | local fallback in code | PostgreSQL connection URL |
| `SESSION_SECRET` | Yes (prod) | auto-generated | Secret for signed admin cookie |
| `ADMIN_USERNAME` | Optional | `arjun` | Initial admin username |
| `ADMIN_PASSWORD` | Optional | `arjun` | Initial admin password |
| `APP_TIMEZONE` | Optional | `Asia/Kolkata` | UI display timezone |

## API Routes (Main)

- `POST /login`
- `GET /logout`
- `POST /api/routine/post`
- `POST /api/routine/reply/{post_id}`
- `GET /api/routine/posts`
- `POST /api/blogs`
- `GET /api/blogs`
- `PUT /api/blogs/{blog_id}`
- `DELETE /api/blogs/{blog_id}`
- `POST /api/contact`

## Deployment (Render)

- Create a Web Service from this repo
- Set build command:
  ```bash
  pip install -r requirements.txt
  ```
- Set start command:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- Add required environment variables in Render dashboard
- Attach PostgreSQL and set `DATABASE_URL`

## Security Notes

- Do not commit real SMTP passwords or secrets.
- Move credentials to environment variables before production use.
- Rotate any secrets that were exposed in code history.

## License

This project is for personal/portfolio use.
