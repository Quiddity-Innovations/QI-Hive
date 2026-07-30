# Free Webhook-Bot Cloud Kit — queue drainer container image
# Build:  docker build -t <bot-name>-drainer .
# Run:    see docker-compose.yml (mounts secrets + AWS creds read-only)
FROM python:3.12-slim

# Never bake secrets into the image — they arrive as read-only volume
# mounts at container start (see docker-compose.yml).
RUN pip install --no-cache-dir boto3 requests

WORKDIR /app
COPY queue_drainer.py .

# Container-side paths; docker-compose.yml maps the host files onto
# these. Override QUEUE_URL / LOCAL_WEBHOOK_URL per-deployment in
# docker-compose.yml — they are intentionally NOT set here so this
# image stays reusable across bots.
ENV CHANNEL_SECRET_ENV_FILE=/secrets/channel.env \
    DRAIN_LOG_FILE=/logs/queue_drain_container.log \
    AWS_SHARED_CREDENTIALS_FILE=/aws/credentials \
    AWS_CONFIG_FILE=/aws/config

CMD ["python", "-u", "queue_drainer.py"]
