# Catatan Deploy - xtm-agent

Bot ini memakai metode polling, sehingga cocok dijalankan di Render, Railway, atau VPS.

## Menjalankan lokal
Salin `.env.example` menjadi `.env`, isi TELEGRAM_BOT_TOKEN dan OPENROUTER_API_KEY,
pasang dependensi dari `requirements.txt`, lalu jalankan `bot.py`.

## Docker
```
docker compose up -d --build
```

## Hosting
Hubungkan repo ini ke Render atau Railway, lalu set environment variable yang sama
seperti isi `.env`.

## Hal penting
- Riwayat percakapan disimpan di memori dan hilang saat restart. Untuk produksi,
  gunakan Redis atau SQLite.
- Varian `:free` OpenRouter dapat berubah; fallback otomatis menanganinya.
