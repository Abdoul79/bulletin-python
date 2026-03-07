FROM python:3.11-slim

# Dépendances système pour WeasyPrint (compatible Debian Trixie)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libgif7 \
    libwebp7 \
    libopenjp2-7 \
    libffi-dev \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Port
EXPOSE 8000

# Lancer l'application
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120

