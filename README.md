# xtm-agent — Telegram AI Agent (OpenRouter + DeepSeek V4.1 Flash)

Bot Telegram yang menjawab pesan lewat OpenRouter API, memakai model `deepseek/deepseek-v4.1-flash:free` dengan fallback otomatis ke `deepseek/deepseek-v4.1-flash`.

## Fitur

- Percakapan multi-turn (riwayat per chat)
- Fallback otomatis antar model + retry saat rate limit (HTTP 429)
- Perintah `/start`, `/reset`, `/model`, `/model2`
- Docker ready + CI (GitHub Actions) + trigger deploy otomatis

## Menjalankan lokal

```bash
cp .env.example .env      # isi TELEGRAM_BOT_TOKEN & OPENROUTER_API_KEY
pip install -r requirements.txt
python bot.py
```

## Docker

```bash
docker compose up -d --build
```

## Deploy

1. Buat bot via `@BotFather` (ambil token) dan buat API key di OpenRouter.
2. Push repo ini ke GitHub.
3. Hubungkan repo ke Render / Railway / Fly.io (deploy dari GitHub).
4. Set environment variable dari `.env` di dashboard hosting (jangan commit `.env`).
5. (Opsional) Simpan Deploy Hook sebagai secret `RENDER_DEPLOY_HOOK` agar workflow CI memicu deploy.

## Environment variables

| Variabel | Wajib | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ya | — |
| `OPENROUTER_API_KEY` | ya | — |
| `OPENROUTER_MODEL` | tidak | `deepseek/deepseek-v4.1-flash:free` |
| `OPENROUTER_FALLBACK_MODELS` | tidak | `deepseek/deepseek-v4.1-flash` |
| `SYSTEM_PROMPT` | tidak | asisten ringkas |
| `MAX_HISTORY` | tidak | `20` |

## Catatan

- Kode memakai **polling**, cocok untuk Render/Railway/VPS. Untuk platform serverless (Vercel/Netlify) perlu webhook.
- Riwayat disimpan di memori; hilang saat restart. Untuk produksi gunakan Redis/SQLite.
- Varian `:free` di OpenRouter bisa berubah sewaktu-waktu; fallback otomatis menanganinya.
