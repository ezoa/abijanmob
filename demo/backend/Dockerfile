# API AbidjanMob — prototype de démo
# Le corpus est copié vers /data/corpus pour reproduire l'arborescence du dépôt
# (routing_engine.py résout data/corpus/network.json via parents[2]).
FROM python:3.12-slim

WORKDIR /demo/backend

COPY demo/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY demo/backend/main.py demo/backend/routing_engine.py demo/backend/live.py demo/backend/analytics.py demo/backend/quartiers.py ./
COPY demo/backend/finance ./finance/
COPY demo/backend/wallets ./wallets/
COPY data/corpus /data/corpus

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
