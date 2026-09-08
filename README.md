# 👗 NextGen AI Virtual Try-On Studio

An AI-powered virtual try-on web application that lets users see how clothing looks on their own body before buying — no changing rooms, no guesswork.

**🔗 Live Demo:** [fashion-ai-app-n4bo.onrender.com](https://fashion-ai-app-n4bo.onrender.com)
*(Free-tier hosting — first load after inactivity may take 30–60s to wake up.)*

---

## 💡 The Idea

Online and in-store shopping both suffer from the same problem: customers can't easily tell how an item of clothing will actually look on them. This app lets a user upload a photo of themselves and a photo of a garment, and generates a realistic image of them wearing it — powered by a multimodal AI model.

## ✨ Features

- **AI-Powered Virtual Try-On** — Realistic garment fitting using an AI diffusion model (OOTDiffusion), with support for **upper-body, lower-body, and dress** categories
- **Single-Deployment Architecture** — Frontend and backend served from one FastAPI app, no separate hosting needed
- **Graceful Degradation** — Automatic retry logic (3 attempts) when the AI service is briefly overloaded, plus a "Demo Mode" fallback so the app never shows a broken experience
- **Privacy by Design** — Uploaded photos are validated, size-limited, processed, and immediately deleted from the server — never permanently stored
- **Production-Minded Backend** — Structured logging, environment-based configuration, request size/type validation, and no hardcoded secrets

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| AI Model | IDM-VTON (via Hugging Face `gradio_client`) |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Deployment | Render (Web Service) |
| Version Control | Git + GitHub |

## 🏗️ Architecture

```
Browser (upload photos)
        │
        ▼
FastAPI Backend (/api/v1/fit-garment)
        │
        ├─▶ Validates file type & size
        ├─▶ Saves to a temporary, non-web-accessible directory
        ├─▶ Calls the AI model (with automatic retry on failure)
        ├─▶ Encodes the result as base64 and returns it
        └─▶ Deletes the temporary files (success or failure)
        │
        ▼
Browser renders the result image
```

The frontend and backend are served from the **same FastAPI app** (via `StaticFiles`), so there's a single deployment and no cross-origin complexity in production.

## 🚀 Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/kush13-05/ai-virtual-tryon.git
cd ai-virtual-tryon

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
# Copy .env.example to .env and fill in your own Hugging Face token
cp .env.example .env

# 4. Run the server
uvicorn app:app --reload

# 5. Open in browser
# http://127.0.0.1:8000
```

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `HF_TOKEN` | Your Hugging Face access token (required) |
| `DEMO_MODE` | `true` returns the uploaded photo instantly for testing/demos without calling the AI service; `false` calls the real AI model |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins |

## 🔒 Security Notes

- No secrets are hardcoded — all sensitive config is loaded from environment variables
- Uploaded images are validated by content type and capped at 8MB
- Temporary files are stored outside the web root and deleted after every request
- Internal error details are logged server-side only; the client only ever receives a safe, generic message

## 📌 Known Limitations

- The AI model runs on a free, publicly shared Hugging Face Space. Under heavy global load it can be slow or briefly unavailable — the app handles this gracefully via retries and a demo-mode fallback rather than crashing. A production deployment would use a dedicated, privately-hosted model instance.
- Result quality depends heavily on the input photos — a plain background, even lighting, and a front-facing pose give noticeably better results than busy/cluttered scenes.

## 👤 Author

Built by [Kush Kumar](https://github.com/kush13-05) as a hands-on data science / full-stack learning project.
