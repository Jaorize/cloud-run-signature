# Utiliser une image Python officielle
FROM python:3.11

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier requirements.txt dans le conteneur
COPY requirements.txt .

# Installer les dépendances via pip
RUN pip install --no-cache-dir -r requirements.txt

# Copier le SDK dans le conteneur
COPY sdk/paapi5_python_sdk/ /app/sdk/paapi5_python_sdk/

# Ajouter le SDK au PYTHONPATH pour qu'il soit accessible
ENV PYTHONPATH "/app/sdk/paapi5_python_sdk:$PYTHONPATH"

# Copier le reste du code de l'application dans le conteneur
COPY . .

# Exposer le port 8080
EXPOSE 8080

# Lancer l'application avec Gunicorn
CMD ["gunicorn", "-b", ":8080", "main:app"]
