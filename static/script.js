// --- JavaScript Controller ---
// Handles live image preview and talks to the FastAPI backend

// Change this if you deploy the backend somewhere other than localhost
const API_BASE_URL = "";

// 1. Image Preview Logic
function previewFile(input, previewId) {
    const files = input.files;
    if (files && files.length > 0) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = document.getElementById(previewId);
            img.src = e.target.result;
            img.style.display = 'block';
        };
        reader.readAsDataURL(files[0]);
    }
}

// 2. Core API Execution Logic
async function runVirtualTryOn() {
    const personInput = document.getElementById('personInput');
    const garmentInput = document.getElementById('garmentInput');

    if (!personInput.files[0] || !garmentInput.files[0]) {
        alert("⚠️ भाई, अपनी फोटो और कपड़े की फोटो दोनों अपलोड करो!");
        return;
    }

    document.getElementById('appLoader').style.display = 'block';
    document.getElementById('resultArea').style.display = 'none';

    const formData = new FormData();
    formData.append("person_image", personInput.files[0]);
    formData.append("garment_image", garmentInput.files[0]);

    try {
        // Correct endpoint: base URL + port + the actual API path
        const response = await fetch(`${API_BASE_URL}/api/v1/fit-garment`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            // Try to read the backend's error message instead of guessing
            let detail = "AI server returned an error.";
            try {
                const errBody = await response.json();
                detail = errBody.detail || detail;
            } catch (_) { /* response wasn't JSON, keep default message */ }
            throw new Error(detail);
        }

        const data = await response.json();

        if (data.status === "success") {
            const finalImg = document.getElementById('finalOutput');
            finalImg.src = data.output_image_url;
            document.getElementById('resultArea').style.display = 'block';
        } else {
            alert("❌ कुछ गड़बड़ हुई, कृपया दोबारा प्रयास करें।");
        }

    } catch (error) {
        console.error("Try-on failed:", error);
        alert(`🔴 एरर: ${error.message}\n\nसुनिश्चित करें कि आपका FastAPI बैकएंड (uvicorn) चल रहा है।`);
    } finally {
        document.getElementById('appLoader').style.display = 'none';
    }
}