import atexit
import os
import re
import shutil
import subprocess
import time
from typing import Dict
from urllib import error as urlerror
from urllib import request as urlrequest


class Tunnel:
    _processes: Dict[str, subprocess.Popen] = {}
    _urls: Dict[str, str] = {}

    def __init__(self):
        atexit.register(self._cleanup)

    @staticmethod
    def _slugify(project_name: str) -> str:
        slug = re.sub(r"[^a-z0-9-]+", "-", (project_name or "").strip().lower())
        slug = re.sub(r"-+", "-", slug).strip("-")
        if not slug:
            slug = "project"
        return f"imposter-{slug}"[:63].rstrip("-")

    @staticmethod
    def _subdomain_with_suffix(base_subdomain: str, suffix: int) -> str:
        if suffix <= 0:
            return base_subdomain
        alt = f"{base_subdomain}-{suffix}"
        return alt[:63].rstrip("-")

    @staticmethod
    def _preview_url(base_url: str, project_name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "", (project_name or "").strip())
        return f"{base_url}/api/project-preview/{safe_name}/"

    @staticmethod
    def _is_url_reachable(url: str, timeout: int = 5) -> bool:
        try:
            with urlrequest.urlopen(url, timeout=timeout) as response:
                return response.status < 500
        except urlerror.HTTPError as http_error:
            # Any HTTP response means the tunnel endpoint is reachable.
            return http_error.code < 500
        except Exception:
            return False

    def _wait_until_reachable(self, base_url: str, project_name: str, attempts: int = 10, delay: int = 1) -> bool:
        probe_urls = [
            base_url,
            f"{base_url}/",
            self._preview_url(base_url, project_name),
        ]

        for _ in range(attempts):
            for probe_url in probe_urls:
                if self._is_url_reachable(probe_url):
                    return True
            time.sleep(delay)
        return False

    @staticmethod
    def _localtunnel_commands(subdomain: str):
        lt_cmd = shutil.which("lt") or shutil.which("lt.cmd") or shutil.which("lt.exe")
        npx_cmd = shutil.which("npx") or shutil.which("npx.cmd")
        bunx_cmd = shutil.which("bunx") or shutil.which("bunx.cmd")

        if not bunx_cmd:
            user_profile = os.environ.get("USERPROFILE", "")
            bunx_candidate = os.path.join(user_profile, ".bun", "bin", "bunx.exe")
            if os.path.exists(bunx_candidate):
                bunx_cmd = bunx_candidate

        commands = []

        if lt_cmd:
            commands.append(
                {
                    "command": [lt_cmd, "--port", "1337", "--subdomain", subdomain],
                    "shell": False,
                    "base_url": f"https://{subdomain}.loca.lt",
                }
            )

        if npx_cmd:
            commands.append(
                {
                    "command": [npx_cmd, "--yes", "localtunnel", "--port", "1337", "--subdomain", subdomain],
                    "shell": False,
                    "base_url": f"https://{subdomain}.loca.lt",
                }
            )

        if bunx_cmd:
            powershell_command = (
                f"& '{bunx_cmd}' --package localtunnel -- lt --port 1337 --subdomain {subdomain}"
            )
            commands.append(
                {
                    "command": [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        powershell_command,
                    ],
                    "shell": False,
                    "base_url": f"https://{subdomain}.loca.lt",
                }
            )
            # Bun's argument parsing can vary by shell/context, so try both forms.
            commands.append(
                {
                    "command": [bunx_cmd, "--package", "localtunnel", "--", "lt", "--port", "1337", "--subdomain", subdomain],
                    "shell": False,
                    "base_url": f"https://{subdomain}.loca.lt",
                }
            )
            commands.append(
                {
                    "command": [bunx_cmd, "localtunnel", "--port", "1337", "--subdomain", subdomain],
                    "shell": False,
                    "base_url": f"https://{subdomain}.loca.lt",
                }
            )

        return commands

    def deploy(self, project_name: str) -> dict:
        if not project_name:
            return {"error": "Project name is required"}

        process = self._processes.get(project_name)
        if process and process.poll() is None:
            tunnel_base = self._urls.get(project_name)
            if tunnel_base and self._wait_until_reachable(tunnel_base, project_name, attempts=2, delay=1):
                return {
                    "deploy_url": self._preview_url(tunnel_base, project_name),
                    "tunnel_url": tunnel_base,
                    "status": "reused",
                }

            try:
                process.terminate()
            except Exception:
                pass
            self._processes.pop(project_name, None)
            self._urls.pop(project_name, None)

        base_subdomain = self._slugify(project_name)
        last_error = ""
        process = None
        tunnel_base = ""
        selected_subdomain = base_subdomain

        for suffix in range(0, 4):
            candidate_subdomain = self._subdomain_with_suffix(base_subdomain, suffix)
            commands = self._localtunnel_commands(candidate_subdomain)
            if not commands:
                return {
                    "error": "Failed to create temporary tunnel. No working tunnel launcher is available.",
                    "details": "Install lt, npx with localtunnel, or bunx with localtunnel available in PATH.",
                }

            for entry in commands:
                command = entry.get("command")
                use_shell = bool(entry.get("shell"))
                try:
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        shell=use_shell,
                    )
                except Exception as error:
                    last_error = f"Command: {' '.join(command)}\n{error}"
                    continue

                time.sleep(2)

                if process.poll() is None:
                    tunnel_base = entry.get("base_url", "")
                    if self._wait_until_reachable(tunnel_base, project_name):
                        selected_subdomain = candidate_subdomain
                        break

                    # Process may still be alive but public endpoint is not usable.
                    try:
                        process.terminate()
                    except Exception:
                        pass
                    process = None
                    last_error = (
                        f"Command: {' '.join(command)}\n"
                        f"Tunnel started but URL was not reachable: {tunnel_base}"
                    )
                    continue

                stderr_output = ""
                try:
                    stderr_output = (process.stderr.read() or "").strip()
                except Exception:
                    stderr_output = ""
                last_error = f"Command: {' '.join(command)}\n{stderr_output}".strip()
                process = None

            if process is not None:
                break

        if process is None:
            return {
                "error": "Failed to create temporary tunnel.",
                "details": last_error,
            }

        self._processes[project_name] = process
        self._urls[project_name] = tunnel_base

        return {
            "deploy_url": self._preview_url(tunnel_base, project_name),
            "tunnel_url": tunnel_base,
            "subdomain": selected_subdomain,
            "status": "started",
        }

    def _cleanup(self):
        for process in self._processes.values():
            try:
                if process and process.poll() is None:
                    process.terminate()
            except Exception:
                continue
