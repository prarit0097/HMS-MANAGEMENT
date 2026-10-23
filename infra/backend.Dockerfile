# Local development image. A production WSGI/ASGI/TLS deployment is a later gate.
FROM python:3.13.17-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system hms && useradd --system --gid hms --home-dir /app hms
COPY --chown=hms:hms backend/manage.py backend/pytest.ini ./
COPY --chown=hms:hms backend/hms ./hms
COPY --chown=hms:hms backend/apps ./apps
COPY --chown=hms:hms backend/tests ./tests
USER hms
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && exec python manage.py runserver 0.0.0.0:8000 --noreload"]
