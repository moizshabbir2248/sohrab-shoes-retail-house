# Vercel Deployment Guide

## 1. Push to GitHub

```bash
git add .
git commit -m "Vercel-ready with Base64 image storage"
git push
```

## 2. Vercel Setup

1. Go to https://vercel.com → Import Project → Import your GitHub repo
2. Framework Preset: **Other**
3. Root Directory: `./` (leave default)

## 3. Environment Variables (set in Vercel Dashboard)

Project Settings → Environment Variables → Add these keys:

```
NEON_DB_URL=postgresql://neondb_owner:npg_xxx@...neon.tech/neondb?sslmode=require
SECRET_KEY=moiz_shoe_store_secret_2026
ADMIN_EMAIL=moizshabbir2248@gmail.com
ADMIN_PASSWORD=abdulmoiz217@
```

Only these **4 keys** needed — no Cloudinary keys, no external storage.

## 4. Deploy

Click **Deploy** on Vercel dashboard. Done.

## Notes

- Images are stored as Base64 data URIs directly in Neon DB
- No file system writes — works perfectly with Vercel serverless (read-only fs)
- DB tables create automatically on first deploy
- Admin session uses cookies (works in serverless)
