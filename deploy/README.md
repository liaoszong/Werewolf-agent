# Werewolf Observer Docker Deploy

This deploys the existing observer server for the mobile client. It does not
change the observer or participant protocol.

## Server Prerequisites

- Ubuntu server with Docker and Docker Compose.
- Firewall allows TCP `8765`.
- DNS `api.paleink.cc` points to the server public IP.

The first public smoke URL is:

```text
http://api.paleink.cc:8765
```

Use this only for early testing. Before submitting real provider keys over the
network, set an observer owner token and prefer HTTPS.

## First Deploy

Clone or update the repository on the server:

```bash
git clone https://github.com/liaoszong/Werewolf-agent.git
cd Werewolf-agent/deploy
```

Start the service:

```bash
sudo docker compose up -d --build
```

If your server user can access Docker without `sudo`, this also works:

```bash
docker compose up -d --build
```

To allow a mobile client outside the server machine to sync provider
credentials for testing, set an owner token outside the repository before
starting the service:

```bash
export WEREWOLF_OBSERVER_OWNER_TOKEN='<generate-a-long-random-token>'
sudo docker compose up -d --build
```

Enter the same value in the Flutter settings page as `Observer owner token`.
Do not commit this value, paste it into logs, or reuse it for long-term
multi-user testing.

## Verify

Check logs:

```bash
sudo docker compose logs -f werewolf-observer
```

Expected startup lines include:

```text
observer_server=started
host=0.0.0.0
port=8765
live_api=enabled
```

Check local health from the server:

```bash
curl http://127.0.0.1:8765/health
```

Check public health from your computer:

```bash
curl http://api.paleink.cc:8765/health
```

The Flutter app server URL should be:

```text
http://api.paleink.cc:8765
```

## Upgrade

```bash
cd ~/Werewolf-agent
git pull
cd deploy
sudo docker compose up -d --build
```

## Stop

```bash
cd ~/Werewolf-agent/deploy
sudo docker compose down
```

Run data is stored in the Docker volume `werewolf_runs` and is not deleted by
`docker compose down`.
