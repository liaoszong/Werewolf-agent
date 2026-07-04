from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployContractTests(unittest.TestCase):
    def test_dockerfile_runs_observer_server_for_public_container(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("python:3.12-slim", dockerfile)
        self.assertIn("EXPOSE 8765", dockerfile)
        self.assertIn("werewolf_eval.run_observer_server", dockerfile)
        self.assertIn("--host", dockerfile)
        self.assertIn("0.0.0.0", dockerfile)
        self.assertIn("--port", dockerfile)
        self.assertIn("8765", dockerfile)
        self.assertIn("--runs-dir", dockerfile)
        self.assertIn("/data/runs", dockerfile)
        self.assertIn("--allow-live-api", dockerfile)

    def test_compose_exposes_observer_port_and_persists_runs(self):
        compose = (ROOT / "deploy" / "docker-compose.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("werewolf-observer", compose)
        self.assertIn("8765:8765", compose)
        self.assertIn("werewolf_runs:/data/runs", compose)
        self.assertIn("unless-stopped", compose)

    def test_deploy_readme_documents_public_health_check(self):
        readme = (ROOT / "deploy" / "README.md").read_text(encoding="utf-8")

        self.assertIn("api.paleink.cc", readme)
        self.assertIn("docker compose up -d", readme)
        self.assertIn("curl http://api.paleink.cc:8765/health", readme)
