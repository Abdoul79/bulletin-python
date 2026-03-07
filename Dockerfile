# Dockerfile
FROM python:3.11-slim

# Installer les dépendances système pour WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libgif7 \
    libwebp6 \
    libopenjp2-7 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer Python et WeasyPrint
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . .

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000"]