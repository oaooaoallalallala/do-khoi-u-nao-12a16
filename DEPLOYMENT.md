# Deployment

## Vercel frontend

The root `vercel.json` publishes `demo/frontend` as a static site. Import the GitHub repository into Vercel and deploy with the default settings; no build command is required.

The static site and the Flask/PyTorch prediction API are separate services. After hosting the API, open **Cài đặt kết nối máy chủ AI** on the site and enter its base URL. The API must allow browser requests from the Vercel domain.

## Prediction API

The API is in `demo/backend/app.py` and needs the Python dependencies in `requirements.txt`, approved sample images under `demo/static/images`, and the trained model. The 215 MRI test images and matching masks in `demo/static` are included for testing and were checked for EXIF metadata. The separate `demo/external-data` source dataset remains excluded from Git.

The model file is about 105 MB and is intentionally excluded from Git by `.gitignore`; GitHub also rejects individual files above 100 MiB. Host the model as a separate artifact or persistent mounted file, then make it available at `/app/unet_best.pth` to the backend.

Vercel's static deployment does not run this Flask/PyTorch API. The root `Dockerfile` prepares the API for a Hugging Face Docker Space on port `7860`. Create a **public Docker Space**, upload this project branch with Git LFS tracking `*.pth`, and add `unet_best.pth` at the repository root. This makes the model downloadable by anyone; do not use this deployment option if the model must remain private.

After the Space finishes building, open **Cài đặt kết nối máy chủ AI** on the Vercel site and enter the Space URL (for example, `https://<space-owner>-<space-name>.hf.space`). The API enables CORS for browser requests. Vercel and the backend are separate services; the frontend does not connect to the API until this URL is set.

The training notebook is published as `main/unet-segmentation-project-public.ipynb` with saved outputs removed. Its original output-filled copy remains local and is excluded because it embeds image data.
