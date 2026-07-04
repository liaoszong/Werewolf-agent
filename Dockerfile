FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY . /app

RUN mkdir -p /data/runs

EXPOSE 8765
VOLUME ["/data/runs"]

CMD ["python", "-m", "werewolf_eval.run_observer_server", "--host", "0.0.0.0", "--port", "8765", "--runs-dir", "/data/runs", "--allow-live-api"]
