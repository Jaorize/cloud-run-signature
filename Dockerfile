# Utiliser une image Python officielle comme base
FROM python:3.9-slim

# Créer un répertoire de travail pour l'application
WORKDIR /app

# Copier les fichiers requirements.txt et installer les dépendances
COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers du projet
COPY . .

# Ajouter le dossier sdk au PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app/sdk"

# Exposer le port sur lequel l'application va s'exécuter
EXPOSE 8080

# Commande pour démarrer Gunicorn avec Flask
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]
