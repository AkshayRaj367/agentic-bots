import json

from src.project import ProjectManager
from src.services import Tunnel
from src.state import AgentState
from src.socket_instance import emit_agent


class Deployer:
    def __init__(self):
        self.project_manager = ProjectManager()
        self.agent_state = AgentState()

    def _emit_state(self, project_name: str, message: str, command: str = "Deploy project"):
        new_state = self.agent_state.new_state()
        new_state["internal_monologue"] = message
        new_state["terminal_session"]["title"] = "Deploy"
        new_state["terminal_session"]["command"] = command
        self.agent_state.add_to_current_state(project_name, new_state)

    def execute(self, project_name: str):
        if not project_name:
            return {
                "message": "I couldn't start a temporary tunnel deployment.",
                "error": "Project name is required",
            }

        self._emit_state(project_name, "Starting temporary deployment...")
        deploy_metadata = Tunnel().deploy(project_name)

        if isinstance(deploy_metadata, dict) and deploy_metadata.get("error"):
            response = {
                "message": "I couldn't start a temporary tunnel deployment.",
                "error": deploy_metadata.get("error"),
                "details": deploy_metadata.get("details"),
            }
        else:
            deploy_url = deploy_metadata.get("deploy_url") if isinstance(deploy_metadata, dict) else None
            response = {
                "message": "Done! I created a temporary tunnel deployment for your project.",
                "deploy_url": deploy_url,
            }

        self._emit_state(project_name, response["message"], command=response.get("deploy_url") or "Deploy project")
        emit_agent("deploy", response)
        self.project_manager.add_message_from_imposter(project_name, json.dumps(response, indent=4))
        return response
