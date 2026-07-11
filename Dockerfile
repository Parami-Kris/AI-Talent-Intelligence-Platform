FROM python:3.11-slim

WORKDIR /app

# libgl1/libglib2.0-0: common runtime deps for Docling's image-processing backends
# (opencv-headless etc.) on Debian slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch/torchvision default to their full CUDA-enabled wheels (500MB+ each,
# plus several hundred MB of nvidia-*/triton CUDA packages) even though this
# app only ever does CPU inference (Docling's layout/table models). Installing
# the CPU-only wheel first means pip resolves the rest of requirements.txt
# against it instead of pulling the GPU build - this alone was likely a large
# part of why Render's free tier ran out of memory/time.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake Docling's models into the image at BUILD time instead of letting them
# download on first request. This is the actual fix for the Render deploy
# failures (OOM / port-scan timeout) - Docling's model download + heavy import
# chain (torch/transformers/docling-ibm-models) was too slow/heavy to do cold,
# on a live request, on a resource-constrained instance. Running a real
# .convert() against a real PDF here forces every model Docling actually needs
# to download and cache into the image now, so the running container never
# has to do it.
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter().convert('Parami_Resume.pdf')"

EXPOSE 7860

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860"]
