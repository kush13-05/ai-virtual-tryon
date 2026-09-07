import os
import uuid
import base64
import asyncio
import logging
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from gradio_client import Client, handle_file

# Load variables from the .env file into the environment (local dev)
load_dotenv()

# --- Logging setup (replaces print()) ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fashion-engine")

app = FastAPI(title="NextGen AI Fashion Engine")

# --- CORS ---
# Now that the frontend (index.html/script.js) is served by this SAME app
# (see StaticFiles mount below), browser requests come from the same origin
# and CORS restrictions barely matter anymore. Kept here mainly in case you
# ever call this API from a different domain later.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Secrets: no hardcoded fallback. App refuses to start without it. ---
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN environment variable is not set. "
        "Create a .env file (see .env.example) and never hardcode tokens in source."
    )

SECURE_STAGE = os.path.join(tempfile.gettempdir(), "fashion_app_secure_stage")
os.makedirs(SECURE_STAGE, exist_ok=True)

MAX_FILE_SIZE_MB = 8
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
AI_MODEL_MAX_RETRIES = 3
AI_MODEL_RETRY_DELAY_SECONDS = 4

# Demo mode: skip the (unreliable, free, shared) AI service entirely and
# just echo the person photo back as the "result" after a short fake delay.
# Lets you show the full upload -> process -> result flow reliably, without
# depending on the external model being awake and unqueued.
# Turn on by adding DEMO_MODE=true to your .env file.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


def _cleanup(*paths):
    """Remove temp files regardless of whether the pipeline succeeded or failed."""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(f"Could not remove {path}: {e}")


async def _save_upload(upload: UploadFile, dest_path: str):
    """Validate type + enforce a size cap while streaming to disk."""
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.content_type}")

    size = 0
    with open(dest_path, "wb") as buffer:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                buffer.close()
                os.remove(dest_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.",
                )
            buffer.write(chunk)


async def _call_ai_model_with_retry(person_path: str, garment_path: str, request_id: str):
    """
    The public IDM-VTON demo is a shared, free model — under heavy load it can
    drop the connection (shows up as heartbeat 404s). Retry a few times with
    a short pause before giving up, instead of failing on the first hiccup.
    """
    last_error = None
    for attempt in range(1, AI_MODEL_MAX_RETRIES + 1):
        try:
            ai_client = Client("yisol/IDM-VTON", token=HF_TOKEN)
            return ai_client.predict(
                dict={"background": handle_file(person_path), "layers": [], "composite": None},
                garm_img=handle_file(garment_path),
                garment_des="Hyper-realistic premium clothing fabric",
                is_checked=True,
                denoise_steps=30,
                seed=42,
                api_name="/tryon",
            )
        except Exception as e:
            last_error = e
            logger.warning(f"[{request_id}] AI model attempt {attempt} failed: {e}")
            if attempt < AI_MODEL_MAX_RETRIES:
                await asyncio.sleep(AI_MODEL_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        "The AI model is busy or unavailable right now (shared free demo model). "
        "Please try again in a minute."
    ) from last_error


@app.get("/health")
async def health_check():
    """Simple liveness check — useful for deployment/monitoring."""
    return {"status": "ok"}


@app.post("/api/v1/fit-garment")
async def fit_garment_pipeline(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
):
    request_id = uuid.uuid4().hex  # unique even under concurrent requests
    logger.info(f"Processing request {request_id}")

    safe_person_path = os.path.join(SECURE_STAGE, f"user_{request_id}.png")
    safe_garment_path = os.path.join(SECURE_STAGE, f"cloth_{request_id}.png")

    try:
        await _save_upload(person_image, safe_person_path)
        await _save_upload(garment_image, safe_garment_path)

        if DEMO_MODE:
            # Fake a short processing delay, then just return the person's
            # own photo back as the "result" — proves the whole pipeline
            # (upload, backend, response, display) works end to end.
            await asyncio.sleep(3)
            with open(safe_person_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return {"status": "success", "output_image_url": f"data:image/png;base64,{encoded}"}

        # AI cluster connection — retries automatically if the shared demo
        # model is briefly overloaded.
        ai_response = await _call_ai_model_with_retry(
            safe_person_path, safe_garment_path, request_id
        )

        # ai_response is a local file path (or tuple of paths) on THIS server's
        # disk — a browser can't load that directly. Read it and send it back
        # as a base64 data URL so <img src="..."> works with zero extra setup.
        output_path = ai_response[0] if isinstance(ai_response, (list, tuple)) else ai_response
        if not output_path or not os.path.exists(output_path):
            raise RuntimeError("AI model did not return a valid output image.")

        ext = os.path.splitext(output_path)[1].lstrip(".").lower() or "png"
        mime = f"image/{'jpeg' if ext == 'jpg' else ext}"
        with open(output_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        output_data_url = f"data:{mime};base64,{encoded}"

        return {"status": "success", "output_image_url": output_data_url}

    except HTTPException:
        # Already a clean, safe-to-return error (bad file type, too large, etc.)
        raise
    except RuntimeError as e:
        # Known, expected failure (AI model unavailable) — safe to show as-is.
        logger.warning(f"[{request_id}] {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        # Log full details server-side only — never leak internals to the client.
        logger.exception(f"Pipeline failure on request {request_id}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your image. Please try again.",
        )
    finally:
        # Privacy: original photos are always wiped, success or failure.
        _cleanup(safe_person_path, safe_garment_path)


# --- Serve the frontend (index.html, script.js, manifest.json) from this
# SAME app, so there's just one link/one deployment for the whole project.
# Mounted LAST so it never shadows the /api/... and /health routes above.
app.mount("/", StaticFiles(directory="static", html=True), name="static")