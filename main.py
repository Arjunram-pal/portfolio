import os
import secrets
import smtplib
import time
import base64
import hashlib
import hmac
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://portfolio_arjunram_user:zawpXuGRfojQ4h9V3g9gtbUafJU8f1lF@dpg-d6cji5jh46gs73citlt0-a.oregon-postgres.render.com/portfolio_arjunram").strip()
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "arjun")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "arjun")
AUTH_COOKIE = "admin_auth"
AUTH_MAX_AGE_SECONDS = 60 * 60 * 24
PBKDF2_ITERATIONS = 200_000

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure PostgreSQL connection string."
        )
    return psycopg2.connect(DATABASE_URL)


class Post(BaseModel):
    message: str


class Reply(BaseModel):
    message: str


class ContactMessage(BaseModel):
    fullname: str
    email: str
    message: str


class BlogPost(BaseModel):
    title: str
    category: str
    content: str


def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    salt_hex = salt_hex or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS
    ).hex()
    return f"{salt_hex}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    computed = hash_password(password, salt_hex=salt_hex).split("$", 1)[1]
    return secrets.compare_digest(computed, expected_digest)


def get_admin_credentials() -> Dict[str, str]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT username, password_hash FROM admin_credentials WHERE id = 1"
            )
            row = cursor.fetchone()

    if row is None:
        return {
            "username": ADMIN_USERNAME,
            "password_hash": hash_password(ADMIN_PASSWORD)
        }
    return {"username": row["username"], "password_hash": row["password_hash"]}


def get_admin_username() -> str:
    return get_admin_credentials()["username"]


def update_admin_credentials(username: str, password_hash: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE admin_credentials
                SET username = %s, password_hash = %s, updated_at = %s
                WHERE id = 1
                """,
                (username, password_hash, datetime.now().isoformat())
            )


def is_admin(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        return False
    return verify_admin_token(token)


def make_signature(payload: str) -> str:
    return hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def build_admin_token(username: str) -> str:
    timestamp = str(int(time.time()))
    payload = f"{username}:{timestamp}"
    signature = make_signature(payload)
    token_raw = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token_raw.encode("utf-8")).decode("utf-8")


def verify_admin_token(token: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        username, timestamp, signature = decoded.split(":", 2)
    except Exception:
        return False

    payload = f"{username}:{timestamp}"
    expected_signature = make_signature(payload)
    if not secrets.compare_digest(signature, expected_signature):
        return False

    if username != get_admin_username():
        return False

    try:
        token_age = int(time.time()) - int(timestamp)
    except ValueError:
        return False

    return token_age <= AUTH_MAX_AGE_SECONDS


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin login required."
        )


def template_context(
    request: Request,
    active_page: str,
    **extra: Any
) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "request": request,
        "active_page": active_page,
        "is_admin": is_admin(request)
    }
    context.update(extra)
    return context


def init_db() -> None:
    """Initialize the database with tables"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id BIGSERIAL PRIMARY KEY,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS replies (
                    id BIGSERIAL PRIMARY KEY,
                    post_id BIGINT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    CONSTRAINT fk_post
                      FOREIGN KEY(post_id)
                      REFERENCES posts(id)
                      ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blogs (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_credentials (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            cursor.execute('SELECT id FROM admin_credentials WHERE id = 1')
            admin_row = cursor.fetchone()
            if admin_row is None:
                cursor.execute(
                    '''
                    INSERT INTO admin_credentials (id, username, password_hash, updated_at)
                    VALUES (1, %s, %s, %s)
                    ''',
                    (
                        ADMIN_USERNAME,
                        hash_password(ADMIN_PASSWORD),
                        datetime.now().isoformat()
                    )
                )


def get_posts_from_db() -> List[Dict[str, Any]]:
    """Fetch all posts with replies from database"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('SELECT id, message, timestamp FROM posts ORDER BY id DESC')
            posts = cursor.fetchall()

            posts_list = []
            for post in posts:
                post_dict = dict(post)
                cursor.execute(
                    'SELECT id, message, timestamp FROM replies WHERE post_id = %s ORDER BY id ASC',
                    (post_dict['id'],)
                )
                post_dict['replies'] = [dict(reply) for reply in cursor.fetchall()]
                posts_list.append(post_dict)

    return posts_list


def get_blogs_from_db() -> List[Dict[str, Any]]:
    """Fetch all blogs from database"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                'SELECT id, title, category, content, timestamp FROM blogs ORDER BY id DESC'
            )
            blogs = cursor.fetchall()

    return [dict(blog) for blog in blogs]


def send_email(fullname: str, sender_email: str, message: str) -> bool:
    """Send email via Gmail SMTP"""
    try:
        gmail_user = "arjunrampal9867@gmail.com"
        gmail_password = "gsgi udvk lwrb kfao"
        recipient_email = "arjunrampal9867@gmail.com"

        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = recipient_email
        msg['Subject'] = f"New Contact from {fullname}"

        body = f"""You have a new message from your portfolio:

Name: {fullname}
Email: {sender_email}

Message:
{message}"""

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


init_db()


def render_login_page(
    request: Request,
    error: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
):
    return templates.TemplateResponse(
        "login.html",
        template_context(
            request,
            "login",
            error=error,
            admin_username=get_admin_username()
        ),
        status_code=status_code
    )


def render_admin_settings_page(
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
):
    return templates.TemplateResponse(
        "admin-settings.html",
        template_context(
            request,
            "settings",
            error=error,
            success=success,
            admin_username=get_admin_username()
        ),
        status_code=status_code
    )


@app.get("/")
async def home():
    return RedirectResponse(url="/about")


@app.get("/login")
def login_page(request: Request):
    if is_admin(request):
        return RedirectResponse(
            url="/admin/settings",
            status_code=status.HTTP_303_SEE_OTHER
        )
    return render_login_page(request)


@app.post("/login")
async def login(
    request: Request
):
    form_data = await request.form()
    username = str(form_data.get("username", "")).strip()
    password = str(form_data.get("password", ""))
    credentials = get_admin_credentials()

    username_ok = secrets.compare_digest(username, credentials["username"])
    password_ok = verify_password(password, credentials["password_hash"])

    if username_ok and password_ok:
        response = RedirectResponse(
            url="/admin/settings",
            status_code=status.HTTP_303_SEE_OTHER
        )
        response.set_cookie(
            key=AUTH_COOKIE,
            value=build_admin_token(username),
            max_age=AUTH_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax"
        )
        return response

    return render_login_page(
        request,
        error="Invalid username or password.",
        status_code=status.HTTP_401_UNAUTHORIZED
    )


@app.get("/admin/settings")
def admin_settings_page(request: Request):
    require_admin(request)
    return render_admin_settings_page(request)


@app.post("/admin/account")
async def update_admin_account(request: Request):
    require_admin(request)
    form_data = await request.form()
    new_username = str(form_data.get("new_username", "")).strip()
    current_password = str(form_data.get("current_password", ""))
    new_password = str(form_data.get("new_password", ""))
    confirm_password = str(form_data.get("confirm_password", ""))

    credentials = get_admin_credentials()
    username_to_save = new_username or credentials["username"]
    password_hash_to_save = credentials["password_hash"]

    if len(username_to_save) < 3:
        return render_admin_settings_page(
            request,
            error="Username must be at least 3 characters.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not verify_password(current_password, credentials["password_hash"]):
        return render_admin_settings_page(
            request,
            error="Current password is incorrect.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    if bool(new_password) != bool(confirm_password):
        return render_admin_settings_page(
            request,
            error="Enter and confirm new password to change it.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if new_password:
        if len(new_password) < 6:
            return render_admin_settings_page(
                request,
                error="New password must be at least 6 characters.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        if not secrets.compare_digest(new_password, confirm_password):
            return render_admin_settings_page(
                request,
                error="New password and confirm password do not match.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        password_hash_to_save = hash_password(new_password)

    update_admin_credentials(username_to_save, password_hash_to_save)

    response = render_admin_settings_page(
        request,
        success="Admin credentials updated successfully."
    )
    response.set_cookie(
        key=AUTH_COOKIE,
        value=build_admin_token(username_to_save),
        max_age=AUTH_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax"
    )
    return response


@app.get("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/about", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(AUTH_COOKIE)
    return response


@app.get("/daily-routine")
async def daily_routine_page(request: Request):
    posts = get_posts_from_db()
    return templates.TemplateResponse(
        "daily-routine.html",
        template_context(request, "daily", posts=posts)
    )


@app.get("/about")
def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        template_context(request, "about")
    )


@app.get("/resume")
def resume(request: Request):
    return templates.TemplateResponse(
        "resume.html",
        template_context(request, "resume")
    )


@app.get("/blog")
def blog(request: Request):
    blogs = get_blogs_from_db()
    return templates.TemplateResponse(
        "blog.html",
        template_context(request, "blog", blogs=blogs)
    )


@app.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse(
        "contact.html",
        template_context(request, "contact")
    )


@app.post("/api/routine/post")
async def create_post(request: Request, post: Post) -> Dict[str, Any]:
    """Create a new daily routine post"""
    require_admin(request)
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO posts (message, timestamp) VALUES (%s, %s) RETURNING id',
                (post.message, timestamp)
            )
            post_id = cursor.fetchone()[0]

    return {
        "id": post_id,
        "message": post.message,
        "timestamp": timestamp,
        "replies": []
    }


@app.post("/api/routine/reply/{post_id}")
async def add_reply(
    post_id: int,
    reply: Reply,
    request: Request
) -> Dict[str, Any]:
    """Add a reply to a post"""
    require_admin(request)
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO replies (post_id, message, timestamp) VALUES (%s, %s, %s) RETURNING id',
                (post_id, reply.message, timestamp)
            )
            reply_id = cursor.fetchone()[0]

    return {
        "id": reply_id,
        "message": reply.message,
        "timestamp": timestamp
    }


@app.get("/api/routine/posts")
async def get_posts() -> List[Dict[str, Any]]:
    """Fetch all posts with replies"""
    return get_posts_from_db()


@app.post("/api/contact")
async def contact(contact: ContactMessage) -> Dict[str, str]:
    """Handle contact form submission and send email"""
    print(f"📨 Contact form received: {contact.fullname} from {contact.email}")
    success = send_email(contact.fullname, contact.email, contact.message)

    if success:
        print("✅ Email sent to arjunrampal9867@gmail.com")
        return {"status": "success", "message": "Email sent successfully!"}
    else:
        print("❌ Failed to send email")
        return {"status": "error", "message": "Failed to send email. Please try again."}


@app.post("/api/blogs")
async def create_blog(request: Request, blog: BlogPost) -> Dict[str, Any]:
    """Create a new blog post"""
    require_admin(request)
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO blogs (title, category, content, timestamp) VALUES (%s, %s, %s, %s) RETURNING id',
                (blog.title, blog.category, blog.content, timestamp)
            )
            blog_id = cursor.fetchone()[0]

    return {
        "id": blog_id,
        "title": blog.title,
        "category": blog.category,
        "content": blog.content,
        "timestamp": timestamp
    }


@app.get("/api/blogs")
async def get_blogs() -> List[Dict[str, Any]]:
    """Fetch all blogs"""
    return get_blogs_from_db()


@app.put("/api/blogs/{blog_id}")
async def update_blog(
    blog_id: int,
    blog: BlogPost,
    request: Request
) -> Dict[str, Any]:
    """Update a blog post"""
    require_admin(request)
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE blogs SET title = %s, category = %s, content = %s, timestamp = %s WHERE id = %s',
                (blog.title, blog.category, blog.content, timestamp, blog_id)
            )

    return {
        "id": blog_id,
        "title": blog.title,
        "category": blog.category,
        "content": blog.content,
        "timestamp": timestamp
    }


@app.delete("/api/blogs/{blog_id}")
async def delete_blog(blog_id: int, request: Request) -> Dict[str, str]:
    """Delete a blog post"""
    require_admin(request)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM blogs WHERE id = %s', (blog_id,))

    return {"status": "success", "message": "Blog deleted successfully!"}
