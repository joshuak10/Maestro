FROM node:22-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web ./
RUN npm run build

FROM python:3.14-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu
COPY app/ app/
COPY models/linear_nsynth.pth models/
COPY --from=frontend /web/dist web/dist

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
