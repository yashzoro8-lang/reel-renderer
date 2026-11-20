FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask gunicorn yt-dlp
WORKDIR /app
COPY app.py .
ENV PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:$PORT -t 1200 -w 1 app:app"]
