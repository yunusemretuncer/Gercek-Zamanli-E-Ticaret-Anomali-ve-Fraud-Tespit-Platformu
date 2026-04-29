FROM python:3.12-slim
WORKDIR /srv
COPY shared /srv/shared
COPY mcp/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp/app /srv/app
CMD ["python", "-m", "app.main"]
