# Speech-to-Text Microservice (WhatsApp Bot Kota Medan)

Microservice independen berbasis **Python**, **FastAPI**, **faster-whisper (CTranslate2)**, dan **FFmpeg** yang dirancang untuk menerima rekaman suara (WhatsApp voice note), melakukan normalisasi audio, dan mengembalikan hasil transkripsi teks Bahasa Indonesia yang cepat, presisi, dan hemat sumber daya.

---

## 🚀 Fitur Utama

- **Cepat & Ringan**: Inferensi CPU menggunakan kuantisasi `int8` dengan *Real-Time Factor* (RTF) berkisar antara `0.1x – 0.7x` (lebih cepat dari durasi audio asli).
- **Domain Tuning Pemko Medan**: Dilengkapi *prompt context* untuk akurasi tinggi terhadap nama instansi (*Dukcapil, Dishub, Kantor Wali Kota*), administrasi (*KTP elektronik, Kartu Keluarga*), dan pengaduan masyarakat.
- **100% Offline & Mandiri**: Model bobot AI disimpan secara lokal tanpa ketergantungan koneksi internet ke Hugging Face.
- **Resource Isolated**: Mengontrol konkurensi (`asyncio.Semaphore`) dan penggunaan core CPU (`STT_CPU_THREADS`) agar stabil berdampingan dengan layanan RAG/AI Agent lain.
- **Stateless & Aman**: Audio diunggah secara *chunked streaming* dan file temporer dijamin bersih seketika (`try...finally`).
- **Autentikasi Aman**: Dilindungi verifikasi header `X-API-Key` dengan *constant-time comparison* untuk mencegah *timing attacks*.
- **Endpoint Terstandar**: Menggunakan prefix jalur `/stt-api/v1` dan port `5001`.

---

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **Framework**: FastAPI + Uvicorn
- **Speech-to-Text Engine**: `faster-whisper` (`small` model, CPU `int8`)
- **Audio Processing**: FFmpeg / FFprobe (dengan fallback PyAV)
- **Containerization**: Docker & Docker Compose (Multi-stage build, non-root user)

---

## 📁 Struktur Arsitektur Modular

```text
├── app/
│   ├── api/
│   │   ├── deps.py              # X-API-Key verification & Dependency injection
│   │   ├── router.py            # Aggregator router prefix /stt-api/v1
│   │   └── v1/
│   │       ├── health.py        # GET /stt-api/v1/health
│   │       └── transcription.py # POST /stt-api/v1/transcriptions
│   ├── core/
│   │   ├── config.py            # Pydantic settings & environment configuration
│   │   ├── constants.py         # Error codes & supported audio formats
│   │   ├── exceptions.py        # Standardized custom business exceptions
│   │   └── logging.py           # Structured JSON logger (Privacy protected)
│   ├── engines/
│   │   ├── base.py              # BaseSTTEngine interface
│   │   └── faster_whisper.py    # Threadpool inference & concurrency semaphore
│   ├── infrastructure/
│   │   ├── ffmpeg.py            # Audio normalization to WAV 16kHz Mono
│   │   ├── ffprobe.py           # Metadata extraction & duration validation
│   │   └── temp_file.py         # Safe temporary file manager (UUID & streaming)
│   ├── middleware/
│   │   ├── error_handler.py     # Global exception handlers (Uniform error format)
│   │   └── request_id.py        # Distributed tracing header X-Request-ID
│   ├── schemas/                 # Pydantic DTO contracts
│   └── main.py                  # FastAPI lifespan & application factory
├── docker/
│   └── Dockerfile               # Multi-stage slim Dockerfile (non-root appuser)
├── docker-compose.yml           # Compose specification with CPU/RAM resource limits
├── requirements.txt             # Python production dependencies
└── scripts/
    ├── benchmark.py             # RTF, latency, and accuracy benchmark runner
    └── download_model.py        # Model extractor/downloader to ./models/
```

---

## ⚙️ Menjalankan Service

### 1. Menggunakan Docker Compose (Direkomendasikan untuk Production)

1. **Siapkan Environment**:
   ```bash
   cp .env.example .env
   ```
   Atur `API_KEY` pada file `.env` dengan token rahasia Anda.

2. **Pastikan Model Tersedia**:
   Jalankan skrip untuk menyiapkan model di folder `./models/small`:
   ```bash
   python scripts/download_model.py --model small
   ```

3. **Jalankan Container**:
   ```bash
   docker compose up -d --build
   ```

Aplikasi akan berjalan pada port `5001`.

---

### 2. Menjalankan secara Lokal (Development)

1. **Buat & Aktifkan Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Instal Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
   ```

---

## 📡 Dokumentasi Endpoint Singkat

Base URL: `http://<HOST>:5001/stt-api/v1`

### 1. Health Check
- **Endpoint**: `GET /stt-api/v1/health`
- **Auth**: Tidak memerlukan API key.
- **Response**:
  ```json
  {
    "status": "ok",
    "engine": "faster_whisper",
    "model": "/app/models/small",
    "device": "cpu"
  }
  ```

### 2. Transcribe Audio
- **Endpoint**: `POST /stt-api/v1/transcriptions`
- **Auth**: Header `X-API-Key: <YOUR_API_KEY>`
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `file`: Berkas audio (`.ogg`, `.mp3`, `.wav`, `.m4a`, dll.)
  - `language`: `id` *(opsional)*
- **Response**:
  ```json
  {
    "success": true,
    "text": "Saya mau tanya, dimana Kantor Wali Kota?",
    "language": "id",
    "duration_seconds": 3.05,
    "processing_time_ms": 712
  }
  ```

---

## 🧪 Menjalankan Pengujian

Jalankan seluruh rangkaian pengujian otomatis (*unit* & *integration tests*):
```bash
pytest -v
```

---

## ⚖️ Lisensi
Dikelola untuk kebutuhan sistem informasi dan bot WhatsApp Pemerintah Kota Medan.
