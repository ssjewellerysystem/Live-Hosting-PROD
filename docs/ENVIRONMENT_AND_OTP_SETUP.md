# Development, production, encryption, and OTP setup

## Deployment environments

The frontend and backend are configured independently:

| Environment | Frontend | Backend | Database |
|---|---|---|---|
| Development | Vercel preview/development project | Render development service | Development Neon database/branch |
| Production | `ssjewellry.com` on Vercel | Oracle Docker backend | Production Neon database/branch |

Recommended Render values:

```env
ENVIRONMENT=DEV
FRONTEND_URL=https://YOUR-DEV-VERCEL-DOMAIN
ALLOWED_ORIGINS=https://YOUR-DEV-VERCEL-DOMAIN
DEV_DATABASE_URL=postgresql://...neon.../...?sslmode=require
EXPOSE_OTP_IN_RESPONSE=false
ENABLE_EMAIL=true
ENABLE_EMAIL_REGISTRATION_OTP=true
SMTP_EMAIL=ssjewellerysystem@gmail.com
SMTP_PASSWORD=<gmail-app-password>
ENABLE_MOBILE_OTP=false
MOBILE_OTP_PROVIDER=disabled
```

Recommended Oracle `/opt/ssjewellery/.env` values:

```env
ENVIRONMENT=PROD
FRONTEND_URL=https://ssjewellry.com
ALLOWED_ORIGINS=https://ssjewellry.com,https://www.ssjewellry.com
PROD_DATABASE_URL=postgresql://...neon.../...?sslmode=require
EXPOSE_OTP_IN_RESPONSE=false
ENABLE_EMAIL=true
ENABLE_EMAIL_REGISTRATION_OTP=true
SMTP_EMAIL=ssjewellerysystem@gmail.com
SMTP_PASSWORD=<gmail-app-password>
ENABLE_MOBILE_OTP=false
MOBILE_OTP_PROVIDER=disabled
```

Set Vercel's `VITE_API_BASE_URL` to the matching backend URL, including `/api`:

```env
# Development Vercel project
VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api

# Production Vercel project
VITE_API_BASE_URL=https://api.ssjewellry.com/api
```

## Encryption-key rule

Docker does not generate or transform the encryption key. Compose passes
`ENCRYPTION_KEY` from `/opt/ssjewellery/.env` into the container.

Every backend that reads the same encrypted Neon rows must use the exact key
that originally encrypted those rows. A different key cannot decrypt existing
data. There are two safe arrangements:

1. Preferred: separate Neon development and production databases/branches,
   each with its own stable encryption key.
2. If Render and Oracle intentionally share one Neon database, configure the
   exact same historical `ENCRYPTION_KEY` on both. This reduces environment
   isolation and is not preferred.

Never generate a new production key during build or deployment. If the original
key has been lost, code cannot recover the encrypted values; restore the key
from a secure backup or restore compatible database data.

`ENCRYPTION_KEY_FINGERPRINT` is an optional non-secret startup guard. It is the
first 16 hexadecimal characters of SHA-256 over the resolved 32-byte key. Set
the same fingerprint beside the corresponding key on Render and Oracle. A
mismatch stops startup before the application can create incompatible data.
Do not use the fingerprint as the encryption key.

## Gmail SMTP

The sender is `ssjewellerysystem@gmail.com`. Enable two-step verification on
the Google account and create a Google App Password. Store that App Password as
`SMTP_PASSWORD` separately in Render and `/opt/ssjewellery/.env`; never commit
it. Registration and password-reset OTP messages are sent synchronously so a
failed SMTP delivery is reported instead of claiming success.

`EXPOSE_OTP_IN_RESPONSE` must remain `false` on Render and production. It may be
set to `true` only for private local development. The code also requires the
application environment to be `DEV`, so it cannot expose an OTP in production.

## Future paid mobile OTP

Mobile delivery is currently a fail-closed provider boundary in
`backend/utils/mobile_otp.py`. It does not call or charge any vendor.

```env
ENABLE_MOBILE_OTP=false
MOBILE_OTP_PROVIDER=disabled
```

When a vendor is selected, implement and test its provider class, callback
signature verification, delivery status, rate limiting, country-code
normalization, billing limits, and runtime credentials. Only then register its
name and set `ENABLE_MOBILE_OTP=true`. OTP values must never be logged.
