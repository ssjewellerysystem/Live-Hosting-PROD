import os
from dotenv import load_dotenv

load_dotenv()

from urllib.parse import urlparse

# Environment Detection & Normalization
raw_env = (
    os.environ.get("ENVIRONMENT")
    or os.environ.get("ENV")
    or os.environ.get("APP_ENV")
    or os.environ.get("FLASK_ENV")
    or "DEV"
).strip().upper()

if raw_env in ("DEVELOPMENT", "DEV"):
    ENVIRONMENT = "DEV"
elif raw_env in ("QA", "TESTING", "STAGING"):
    ENVIRONMENT = "QA"
elif raw_env in ("PRODUCTION", "PROD"):
    ENVIRONMENT = "PROD"
else:
    ENVIRONMENT = "DEV"

IS_DEV = (ENVIRONMENT == "DEV")
IS_QA = (ENVIRONMENT == "QA")
IS_PROD = (ENVIRONMENT == "PROD")
IS_PRODUCTION = IS_PROD  # Backward compatibility alias

def _normalize_origin(origin):
    """Normalize one exact browser origin without weakening it to a wildcard."""
    normalized = str(origin or "").strip().rstrip("/")
    if normalized == "*":
        raise ValueError("Wildcard CORS origins are not allowed with credentials")
    return normalized


def get_allowed_origins(frontend_url=None, allowed_origins=None, environment=None):
    """
    Build the ordered, de-duplicated list of exact credentialed CORS origins.

    Optional arguments make the resolver independently testable. Normal application
    startup reads FRONTEND_URL and ALLOWED_ORIGINS directly from the environment.
    """
    origins = []
    frontend_value = os.environ.get("FRONTEND_URL", "") if frontend_url is None else frontend_url
    allowed_value = os.environ.get("ALLOWED_ORIGINS", "") if allowed_origins is None else allowed_origins

    for configured_value in (frontend_value, allowed_value):
        for candidate in str(configured_value or "").split(","):
            origin = _normalize_origin(candidate)
            if origin and origin not in origins:
                origins.append(origin)

    active_environment = str(environment or ENVIRONMENT).strip().upper()
    dev_defaults = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5005",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5005"
    ]
    if active_environment not in ("PROD", "PRODUCTION"):
        for default_origin in dev_defaults:
            if default_origin not in origins:
                origins.append(default_origin)

    return origins


# Centralized Frontend URL used for redirects and application links.
FRONTEND_URL = _normalize_origin(
    os.environ.get("FRONTEND_URL") or ("http://localhost:5173" if not IS_PROD else "")
)


# Dynamic Database URI resolution based on ENVIRONMENT
base_dir = os.path.dirname(os.path.abspath(__file__))
sqlite_dev_path = os.path.join(base_dir, 'dev.db').replace('\\', '/')

if ENVIRONMENT == "DEV":
    # 1. DEVELOPMENT Database URL
    raw_uri = (
        os.environ.get("DEV_DATABASE_URL")
        or os.environ.get("DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{sqlite_dev_path}"
    )
elif ENVIRONMENT == "QA":
    # 2. QA Database URL (Paste your QA Database link inside quotes below)
    raw_uri = (
        os.environ.get("QA_DATABASE_URL")
        or os.environ.get("DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{sqlite_dev_path}"
    )
else:
    # 3. PRODUCTION Database URL (Paste your Production Database link inside quotes below)
    raw_uri = (
        os.environ.get("PROD_DATABASE_URL")
        or os.environ.get("DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or None
    )




if raw_uri and raw_uri.startswith("postgres://"):
    raw_uri = raw_uri.replace("postgres://", "postgresql://", 1)

def _get_bool_env(var_name, default_bool):
    val = os.environ.get(var_name)
    if val is None:
        return default_bool
    return str(val).strip().lower() in ("true", "1", "yes", "on", "enabled")

class Config:
    ENVIRONMENT = ENVIRONMENT
    ENV = ENVIRONMENT.lower()
    IS_DEV = IS_DEV
    IS_QA = IS_QA
    IS_PROD = IS_PROD
    IS_PRODUCTION = IS_PRODUCTION
    FRONTEND_URL = FRONTEND_URL
    
    # Secrets
    JWT_SECRET = os.environ.get("JWT_SECRET") or (None if IS_PROD else "development-only-change-me")
    SECRET_KEY = os.environ.get("SECRET_KEY") or JWT_SECRET
    JWT_SECRET_KEY = JWT_SECRET

    # Cookie & Session Security Settings (Environment Aware)
    SESSION_COOKIE_SECURE = not IS_DEV
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "None" if not IS_DEV else "Lax"
    REMEMBER_COOKIE_SECURE = not IS_DEV
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "None" if not IS_DEV else "Lax"

    JWT_COOKIE_SECURE = not IS_DEV
    JWT_COOKIE_SAMESITE = "None" if not IS_DEV else "Lax"
    JWT_COOKIE_CSRF_PROTECT = False

    @classmethod
    def get_jwt_secret(cls):
        """
        Dynamically retrieve the active JWT secret at runtime across environments.
        """
        return (
            os.environ.get("JWT_SECRET") or cls.JWT_SECRET
        )

    
    # Database
    SQLALCHEMY_DATABASE_URI = raw_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = IS_DEV
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_timeout": 30,
        "pool_size": 10,
        "max_overflow": 5,
    }

    # Centralized Feature Flags (Defaults derived automatically from ENVIRONMENT)
    # DEV: Off by default for isolation
    # QA & PROD: On by default
    default_feature_flag = not IS_DEV
    
    ENABLE_PAYMENT = _get_bool_env("ENABLE_PAYMENT", default_feature_flag)
    ENABLE_SMS = _get_bool_env("ENABLE_SMS", default_feature_flag)
    ENABLE_OTP = _get_bool_env("ENABLE_OTP", default_feature_flag)
    ENABLE_EMAIL = _get_bool_env("ENABLE_EMAIL", True)
    ENABLE_ORDER_CONFIRMATION = _get_bool_env("ENABLE_ORDER_CONFIRMATION", True)
    ENABLE_EMAIL_FORGOT_PASSWORD_OTP = _get_bool_env("ENABLE_EMAIL_FORGOT_PASSWORD_OTP", True)
    ENABLE_EMAIL_ORDER_CONFIRMATION = _get_bool_env("ENABLE_EMAIL_ORDER_CONFIRMATION", True)
    ENABLE_EMAIL_BUY_REQUEST_CONFIRMATION = _get_bool_env("ENABLE_EMAIL_BUY_REQUEST_CONFIRMATION", True)
    ENABLE_EMAIL_REGISTRATION_OTP = _get_bool_env("ENABLE_EMAIL_REGISTRATION_OTP", False)
    ENABLE_PUSH_NOTIFICATIONS = _get_bool_env("ENABLE_PUSH_NOTIFICATIONS", default_feature_flag)
    ENABLE_WEBHOOKS = _get_bool_env("ENABLE_WEBHOOKS", default_feature_flag)
    ENABLE_ANALYTICS = _get_bool_env("ENABLE_ANALYTICS", default_feature_flag)
    ENABLE_RAPID_API = _get_bool_env("ENABLE_RAPID_API", True)

    # Logging Level
    LOGGING_LEVEL = os.environ.get("LOG_LEVEL") or ("DEBUG" if IS_DEV else ("INFO" if IS_QA else "WARNING"))

    # Rapid API Configuration (Auto-resolves based on environment)
    if IS_DEV:
        RAPID_API_KEY = os.environ.get("DEV_RAPID_API_KEY") or os.environ.get("RAPID_API_KEY")
    elif IS_QA:
        RAPID_API_KEY = os.environ.get("QA_RAPID_API_KEY") or os.environ.get("RAPID_API_KEY")
    else:
        RAPID_API_KEY = os.environ.get("PROD_RAPID_API_KEY") or os.environ.get("RAPID_API_KEY")

    # Payment Gateway Credentials (Auto-resolves based on environment)
    if IS_DEV:
        RAZORPAY_KEY_ID = None
        RAZORPAY_KEY_SECRET = None
    elif IS_QA:
        RAZORPAY_KEY_ID = os.environ.get("QA_RAZORPAY_KEY_ID") or os.environ.get("RAZORPAY_KEY_ID")
        RAZORPAY_KEY_SECRET = os.environ.get("QA_RAZORPAY_KEY_SECRET") or os.environ.get("RAZORPAY_KEY_SECRET")
    else:  # PROD
        RAZORPAY_KEY_ID = os.environ.get("PROD_RAZORPAY_KEY_ID") or os.environ.get("RAZORPAY_KEY_ID")
        RAZORPAY_KEY_SECRET = os.environ.get("PROD_RAZORPAY_KEY_SECRET") or os.environ.get("RAZORPAY_KEY_SECRET")

    # Centralized Gmail SMTP Configuration Constants
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_TLS = True

    # Sensitive SMTP Credentials (Runtime OS Environment Variables Only)
    SMTP_EMAIL = os.environ.get("SMTP_EMAIL") or os.environ.get("MAIL_USERNAME") or os.environ.get("EMAIL_ADDRESS")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") or os.environ.get("MAIL_PASSWORD") or os.environ.get("EMAIL_APP_PASSWORD")
    SMTP_FROM = f"SSJewellery <{SMTP_EMAIL}>" if SMTP_EMAIL else None

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    REPORT_SCHEDULER_ENABLED = _get_bool_env("REPORT_SCHEDULER_ENABLED", False)

    # Flask-Mail Compatibility Configuration
    MAIL_SERVER = SMTP_HOST
    MAIL_PORT = SMTP_PORT
    MAIL_USE_TLS = SMTP_TLS
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False").lower() in ("true", "1", "yes")
    MAIL_USERNAME = SMTP_EMAIL
    MAIL_PASSWORD = SMTP_PASSWORD
    MAIL_DEFAULT_SENDER = SMTP_FROM

    # OAuth Credentials
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET")

    # Storage Credentials (Cloudinary)
    if IS_DEV:
        CLOUDINARY_CLOUD_NAME = os.environ.get("DEV_CLOUDINARY_CLOUD_NAME") or os.environ.get("CLOUDINARY_CLOUD_NAME")
        CLOUDINARY_API_KEY = os.environ.get("DEV_CLOUDINARY_API_KEY") or os.environ.get("CLOUDINARY_API_KEY")
        CLOUDINARY_API_SECRET = os.environ.get("DEV_CLOUDINARY_API_SECRET") or os.environ.get("CLOUDINARY_API_SECRET")
    elif IS_QA:
        CLOUDINARY_CLOUD_NAME = os.environ.get("QA_CLOUDINARY_CLOUD_NAME") or os.environ.get("CLOUDINARY_CLOUD_NAME")
        CLOUDINARY_API_KEY = os.environ.get("QA_CLOUDINARY_API_KEY") or os.environ.get("CLOUDINARY_API_KEY")
        CLOUDINARY_API_SECRET = os.environ.get("QA_CLOUDINARY_API_SECRET") or os.environ.get("CLOUDINARY_API_SECRET")
    else:
        CLOUDINARY_CLOUD_NAME = os.environ.get("PROD_CLOUDINARY_CLOUD_NAME") or os.environ.get("CLOUDINARY_CLOUD_NAME")
        CLOUDINARY_API_KEY = os.environ.get("PROD_CLOUDINARY_API_KEY") or os.environ.get("CLOUDINARY_API_KEY")
        CLOUDINARY_API_SECRET = os.environ.get("PROD_CLOUDINARY_API_SECRET") or os.environ.get("CLOUDINARY_API_SECRET")

def validate_smtp_configuration():
    """
    Startup Validation for Gmail SMTP configuration.
    Verifies presence of SMTP_EMAIL and SMTP_PASSWORD runtime environment variables.
    If missing, logs a clear warning without crashing the application.
    """
    smtp_email = Config.SMTP_EMAIL
    smtp_password = Config.SMTP_PASSWORD

    missing_items = []
    if not smtp_email:
        missing_items.append("SMTP_EMAIL")
    if not smtp_password:
        missing_items.append("SMTP_PASSWORD")

    if missing_items:
        print("\n" + "="*70)
        print(" [SMTP CONFIGURATION WARNING] Missing Required OS Environment Variable(s):")
        for item in missing_items:
            print(f"   - {item}")
        print(" Warning: Gmail SMTP email transmission will fail until set in OS Environment.")
        print(" Note: All other website functionality will continue operating normally.")
        print("="*70 + "\n")
    else:
        print("[SMTP SUCCESS] SMTP runtime environment configuration validated.")

def validate_environment():
    """
    Startup environment validation module for backend.
    Validates active ENVIRONMENT (DEV, QA, PROD) configuration.
    """
    print(f"\n[CONFIG] Initializing Enterprise Environment Architecture...")
    print(f"[CONFIG] Active Environment: {ENVIRONMENT}")
    print(f"[CONFIG] Feature Flags: PAYMENT={Config.ENABLE_PAYMENT}, SMS={Config.ENABLE_SMS}, OTP={Config.ENABLE_OTP}, EMAIL={Config.ENABLE_EMAIL}, ORDER_CONF={Config.ENABLE_ORDER_CONFIRMATION}, RAPID_API={Config.ENABLE_RAPID_API}, ANALYTICS={Config.ENABLE_ANALYTICS}")
    print(f"[CONFIG] Logging Level: {Config.LOGGING_LEVEL}\n")

    validate_smtp_configuration()

    if IS_DEV:
        print(f"[CONFIG SUCCESS] Application initialized in DEVELOPMENT mode (FRONTEND_URL: {FRONTEND_URL or 'http://localhost:5173'}).")
        return

    if IS_QA:
        print(f"[CONFIG SUCCESS] Application initialized in QA mode.")
        return

    # Production Strict Checks
    missing = []
    invalid = []

    env_frontend = os.environ.get("FRONTEND_URL")
    if not env_frontend:
        missing.append("FRONTEND_URL")
    elif "localhost" in env_frontend or "127.0.0.1" in env_frontend:
        invalid.append("FRONTEND_URL cannot point to localhost/127.0.0.1 in production mode")

    env_db = Config.SQLALCHEMY_DATABASE_URI
    if not env_db:
        missing.append("PROD_DATABASE_URL / DATABASE_URL / DATABASE_URI")
    else:
        parsed_db = urlparse(env_db)
        if parsed_db.scheme not in ("postgresql", "postgresql+psycopg2"):
            invalid.append("Production database URL must use PostgreSQL")
        if parsed_db.hostname and parsed_db.hostname.endswith("neon.tech"):
            sslmode = dict(part.split("=", 1) for part in parsed_db.query.split("&") if "=" in part).get("sslmode")
            if sslmode not in ("require", "verify-ca", "verify-full"):
                invalid.append("Neon PostgreSQL connections must require SSL")

    env_jwt = os.environ.get("JWT_SECRET")
    if not env_jwt:
        missing.append("JWT_SECRET")
    if not os.environ.get("SECRET_KEY"):
        missing.append("SECRET_KEY")
    if not os.environ.get("ENCRYPTION_KEY"):
        missing.append("ENCRYPTION_KEY")
    if Config.ENABLE_EMAIL and (not Config.SMTP_EMAIL or not Config.SMTP_PASSWORD):
        missing.append("SMTP_EMAIL and SMTP_PASSWORD (required while ENABLE_EMAIL=true)")

    if missing or invalid:
        err_lines = [
            "\n" + "="*75,
            " [CRITICAL DEPLOYMENT SAFETY FAILURE] Production Environment Validation Error!",
            "="*75
        ]
        if missing:
            err_lines.append(" Missing Required Production Environment Variables:")
            for m in missing:
                err_lines.append(f"   - {m}")
        if invalid:
            err_lines.append(" Invalid Production Configuration:")
            for inv in invalid:
                err_lines.append(f"   - {inv}")
        err_lines.append(" Application startup aborted to prevent broken/insecure production deployment.")
        err_lines.append("="*75 + "\n")
        
        error_msg = "\n".join(err_lines)
        print(error_msg)
        raise RuntimeError(error_msg)

    print("[CONFIG SUCCESS] Environment validation passed in PRODUCTION mode.")

