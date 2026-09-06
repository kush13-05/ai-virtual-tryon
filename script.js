// --- HUMANIZED JAVASCRIPT CONTROLLER ---
// Handles live image stream preview and routes data safely to FastAPI backend

// 1. Image Preview Logic
function previewFile(input, previewId) {
    const files = input.files;
    if (files && files.length > 0) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.getElementById(previewId);
            img.src = e.target.result;
            img.style.display = 'block';
        }
        reader.readAsDataURL(files[0]); // Reading the exact file stream
    }
}

// 2. Core API Execution Logic
async function runVirtualTryOn() {
    const personInput = document.getElementById('personInput');
    const garmentInput = document.getElementById('garmentInput');

    if (!personInput.files[0] || !garmentInput.files[0]) {
        alert("⚠️ भाई, अपनी फोटो और कपड़े की फोटो दोनों अपलोड करो!");
        return;
    }

    // Toggle Loading Screen UI
    document.getElementById('appLoader').style.display = 'block';
    document.getElementById('resultArea').style.display = 'none';

    // Pack streams into multi-part form data
    const formData = new FormData();
    formData.append("person_image", personInput.files[0]);
    formData.append("garment_image", garmentInput.files[0]);

    try {
        console.log("[API LOG] Dispatching secure stream to local Python server...");
        
        // Handshake with our running Python FastAPI server (Port 8000)
        const response = await fetch("http://127.0.0", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("AI Server internal timeout or network glitch.");
        }

        const data = await response.json();
        
        if (data.status === "success") {
            const finalImg = document.getElementById('finalOutput');
            finalImg.src = data.output_image_url;
            document.getElementById('resultArea').style.display = 'block';
            console.log("[API LOG] AI Image rendered successfully on UI.");
        } else {
            alert("❌ कुछ गड़बड़ हुई, कृपया दोबारा प्रयास करें।");
        }

    } catch (error) {
        console.error("Critical Glitch:", error);
        alert("🔴 एरर: सर्वर से कनेक्शन नहीं हो पाया। सुनिश्चित करें कि आपका FastAPI बैकएंड चल रहा है।");
    } finally {
        document.getElementById('appLoader').style.display = 'none';
    }
}
