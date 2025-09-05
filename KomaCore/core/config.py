# core/config.py
import os
ENV = os.getenv("ENV", "dev"); IS_PROD = ENV == "prod"

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
X_API_KEYS = [s.strip() for s in os.getenv("X_API_KEYS", os.getenv("X_API_KEY","")).split(",") if s.strip()]
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS","").split(",") if o.strip()]
RATE_LIMIT = os.getenv("RATE_LIMIT", "60/minute")

DSR_CAP_SALARIED = float(os.getenv("DSR_CAP_SALARIED", "0.40"))
DSR_CAP_SELFEMP  = float(os.getenv("DSR_CAP_SELFEMP",  "0.30"))
STRESS_RATE_FLOOR = float(os.getenv("STRESS_RATE_FLOOR", "0.06"))
LTV_CAP_DEFAULT   = float(os.getenv("LTV_CAP_DEFAULT",   "0.50"))

if IS_PROD and (not SESSION_SECRET or not X_API_KEYS):
    raise RuntimeError("Missing required secrets in prod: SESSION_SECRET / X_API_KEYS")