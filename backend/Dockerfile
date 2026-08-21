FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY models/ models/
COPY data/ data/

EXPOSE 4000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "4000"]
