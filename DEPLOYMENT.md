Deployment checklist

This project can run without Redis, but for production you should configure a managed Redis instance for caching, Celery backend, and rate-limiting.

Required / recommended environment variables

- `DATABASE_URL` - PostgreSQL URL (recommended) or leave unset to use SQLite fallback.
- `SECRET_KEY` - Flask secret key (should be a random value in production).
- `JWT_SECRET_KEY` - Optional; defaults to `SECRET_KEY`.
- `REDIS_URL` - Redis URL used for caching and Celery, e.g. `redis://:password@host:6379/0`.
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` - If not set, default to `REDIS_URL`.
- `RATELIMIT_STORAGE_URI` - Storage backend for Flask-Limiter. If not set and `REDIS_URL` is provided, the app will attempt to use Redis. If Redis is unreachable, the app will fall back to `memory://`.
- `DISABLE_RATELIMIT` - Set to `true` to force the app to use in-memory rate limiting (useful for quick deploys without Redis).
- `LOG_TO_STDOUT` - Set to `true` to output logs to stdout (platform-friendly).

Recommendations

- Use a managed Redis provider (Render Redis, Upstash, Railway addon, AWS Elasticache) and set `REDIS_URL` in your service environment.
- For production, set `DATABASE_URL` to a managed Postgres and run migrations.

If you need help wiring a Redis instance into your Render service, tell me the provider and I will provide exact instructions and example `REDIS_URL` formats.
