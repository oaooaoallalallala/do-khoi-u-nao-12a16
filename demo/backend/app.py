from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import torch
import numpy as np
import cv2
import os
import io
import base64
from PIL import Image
import segmentation_models_pytorch as smp

# =========================
# CONFIG
# =========================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("FLASK_ENV", "development") == "development"

print(f"🚀 Starting app on port {PORT}, debug mode: {DEBUG}")
print(f"🖥️  Using device: {DEVICE}")

# =========================
# LOAD MODEL
# =========================
def load_model():
    model = smp.UnetPlusPlus(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=3,
        classes=1
    )
    
    # Try different model paths for different environments
    model_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "unet_best.pth"),
        "unet_best.pth",
        "/app/unet_best.pth"
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        raise FileNotFoundError("Model file not found in any expected location")
        
    print(f"📦 Loading model from: {model_path}")
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    print(f"✅ Model loaded successfully on {DEVICE}")
    return model

try:
    model = load_model()
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

# =========================
# INIT FLASK
# =========================
app = Flask(
    __name__,
    template_folder="../frontend",   # index.html ở đây
    static_folder="../frontend"      # css, js cũng ở đây
)

# Enable CORS for all routes (development and production)
try:
    CORS(app)
    print("✅ CORS enabled")
except:
    print("⚠️  CORS not available, using manual headers")

# Add a route to serve static images
@app.route('/static/images/<filename>')
def serve_image(filename):
    app_root = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(app_root, "..", "static", "images")
    return app.send_from_directory(img_dir, filename)

# Health check endpoint for Render
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "device": DEVICE
    })

@app.route('/test-images')
def test_images():
    app_root = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(app_root, "..", "static", "images")
    files = [
        filename for filename in os.listdir(img_dir)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg'))
    ] if os.path.isdir(img_dir) else []
    return jsonify(sorted(files, key=str.casefold))

# =========================
# HELPER FUNCTIONS
# =========================
def preprocess_image(image: Image.Image):
    img = np.array(image)
    img_resized = cv2.resize(img, (256, 256)) / 255.0
    x_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).unsqueeze(0).float().to(DEVICE)
    return img, x_tensor

def predict_mask(x_tensor, original_img):
    if model is None:
        raise RuntimeError("Model not loaded")
        
    with torch.no_grad():
        pred = model(x_tensor)
        pred = torch.sigmoid(pred).squeeze().cpu().numpy()
    mask = cv2.resize(pred, (original_img.shape[1], original_img.shape[0]))
    mask_bin = (mask > 0.6).astype(np.uint8) * 255

    # Tạo overlay
    mask_color = np.zeros_like(original_img)
    mask_color[mask_bin == 255] = (255, 0, 0)
    overlay = cv2.addWeighted(mask_color, 0.4, original_img, 0.6, 0)
    return mask_bin, overlay

def pil_to_base64(pil_img):
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    # Get the absolute path to the demo directory
    app_root = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(app_root, "..", "static", "images")
    files = []
    
    if os.path.exists(test_dir):
        files = [f for f in os.listdir(test_dir) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        print(f"✅ Found {len(files)} test images")
    else:
        print(f"❌ Test directory not found: {test_dir}")
    
    return render_template("index.html", test_files=files)

@app.route("/predict", methods=["POST"])
def predict():
    if "image" in request.files:     
        file = request.files["image"]
        image = Image.open(file).convert("RGB")

        # Predict
        original_img, x_tensor = preprocess_image(image)
        pred_mask_bin, overlay = predict_mask(x_tensor, original_img)

        # Convert sang PIL
        original_pil = Image.fromarray(original_img)
        pred_mask_pil = Image.fromarray(pred_mask_bin)
        overlay_pil = Image.fromarray(overlay)
        return jsonify({
            "real": pil_to_base64(original_pil),
            "mask": pil_to_base64(pred_mask_pil),
            "mask_gt": "",
            "overlay": pil_to_base64(overlay_pil),
            "overlay_gt": ""
})
    elif "test_image" in request.form:  # Ảnh từ test set
        filename = request.form["test_image"]
        
        app_root = os.path.dirname(os.path.abspath(__file__))
        img_dir  = os.path.join(app_root, "..", "static", "images")
        mask_dir = os.path.join(app_root, "..", "static", "masks")

        img_path = os.path.join(img_dir, filename)
        if not os.path.exists(img_path):
            return jsonify({"error": f"Image not found: {filename}"}), 404

        # Ảnh gốc
        image = Image.open(img_path).convert("RGB")
        original_img, x_tensor = preprocess_image(image)

        # Predict để tạo OVERLAY từ mask predict
        pred_mask_bin, overlay = predict_mask(x_tensor, original_img)

        # Tìm mask gốc (ưu tiên trùng tên; nếu không có thì thử thêm _mask trước đuôi mở rộng)
        mask_path = os.path.join(mask_dir, filename)
        if not os.path.exists(mask_path):
            name, ext = os.path.splitext(filename)
            mask_path_alt = os.path.join(mask_dir, f"{name}_mask{ext}")
            mask_path = mask_path_alt if os.path.exists(mask_path_alt) else None

        if mask_path and os.path.exists(mask_path):
        # Đọc mask ground truth
            mask_gt_img = Image.open(mask_path).convert("L").resize((original_img.shape[1], original_img.shape[0]))
            mask_gt_np = np.array(mask_gt_img)

                # Tạo overlay ground truth
            mask_color = np.zeros_like(original_img)
            mask_color[mask_gt_np > 127] = (0, 255, 0)  # xanh lá cho ground truth
            overlay_gt = cv2.addWeighted(mask_color, 0.4, original_img, 0.6, 0)

                 # Convert sang base64
            mask_gt_b64 = pil_to_base64(mask_gt_img)
            overlay_gt_b64 = pil_to_base64(Image.fromarray(overlay_gt))
        else:
            mask_gt_b64 = ""
            overlay_gt_b64 = ""  # không tìm thấy mask gốc

    else:
        return jsonify({"error": "No image provided"}), 400

    # Chuẩn bị trả về
    original_pil = Image.fromarray(original_img)
    pred_mask_pil = Image.fromarray(pred_mask_bin)
    overlay_pil = Image.fromarray(overlay)

    return jsonify({
        "real": pil_to_base64(original_pil),
        "mask": pil_to_base64(pred_mask_pil),
        "mask_gt": mask_gt_b64,
        "overlay": pil_to_base64(overlay_pil),
        "overlay_gt": overlay_gt_b64    
})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
