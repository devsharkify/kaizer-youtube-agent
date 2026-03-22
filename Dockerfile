FROM python:3.11-slim

# Install FFmpeg + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-dejavu-core \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

# Create assets dir
RUN mkdir -p assets

CMD ["python", "main.py"]
