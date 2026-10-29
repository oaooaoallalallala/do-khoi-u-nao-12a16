# Deployment

## Vercel frontend

The root `vercel.json` publishes `demo/frontend` as a static site. Import the GitHub repository into Vercel and deploy with the default settings; no build command is required.

The static site and the Flask/PyTorch prediction API are separate services. After hosting the API, open **Cài đặt kết nối máy chủ AI** on the site and enter its base URL. The API must allow browser requests from the Vercel domain.

## Prediction API

The API is in `demo/backend/app.py` and needs the Python dependencies in `requirements.txt`, approved sample images under `demo/static/images`, and the trained model. MRI datasets and masks are excluded from Git to avoid publishing potentially sensitive medical images. Add only images that are confirmed de-identified and cleared for redistribution.

The model file is about 105 MB and is intentionally excluded from Git by `.gitignore`; GitHub also rejects individual files above 100 MiB. Host the model as a separate artifact or persistent mounted file, then make it available at `/app/unet_best.pth` to the backend.

Vercel's static deployment does not run this Flask/PyTorch API. Deploy it on a Python-capable service that supports the model and dependencies, then configure its URL in the frontend.

The training notebook is published as `main/unet-segmentation-project-public.ipynb` with saved outputs removed. Its original output-filled copy remains local and is excluded because it embeds image data.
