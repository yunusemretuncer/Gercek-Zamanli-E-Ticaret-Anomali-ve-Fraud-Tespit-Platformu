FROM python:3.12-slim
WORKDIR /srv
COPY shared /srv/shared
COPY worker/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/app /srv/app
CMD ["python", "-m", "app.main"]
