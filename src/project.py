import os
import json
import zipfile
import re
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from src.socket_instance import emit_agent
from sqlmodel import Field, Session, SQLModel, create_engine
from src.config import Config


class Projects(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project: str
    description: str = ""
    tech_stack: str = ""
    created_at: str = ""
    message_stack_json: str


class ProjectManager:
    def __init__(self):
        config = Config()
        sqlite_path = config.get_sqlite_db()
        self.project_path = config.get_projects_dir()
        self.engine = create_engine(f"sqlite:///{sqlite_path}")
        SQLModel.metadata.create_all(self.engine)
        self._ensure_project_columns()

    def _ensure_project_columns(self):
        with Session(self.engine) as session:
            result = session.exec(text("PRAGMA table_info(projects)"))
            columns = {row[1] for row in result}

            expected_columns = {
                "description": "TEXT DEFAULT ''",
                "tech_stack": "TEXT DEFAULT ''",
                "created_at": "TEXT DEFAULT ''",
            }

            for column_name, column_definition in expected_columns.items():
                if column_name not in columns:
                    session.exec(text(f"ALTER TABLE projects ADD COLUMN {column_name} {column_definition}"))
            session.commit()

    def new_message(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "from_imposter": True,
            "message": None,
            "timestamp": timestamp
        }

    @staticmethod
    def _canonical_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (name or "").lower())

    def _project_path_candidates(self, project: str):
        raw = (project or "")
        trimmed = raw.strip()

        candidates = []
        for value in {
            raw,
            trimmed,
            trimmed.lower(),
            trimmed.lower().replace(" ", "-"),
            trimmed.lower().replace(" ", "_"),
            trimmed.lower().replace("_", "-"),
            trimmed.lower().replace("-", "_"),
            raw.lower().replace(" ", "-"),  # legacy behavior (keeps trailing spaces as '-')
        }:
            if value:
                candidates.append(os.path.join(self.project_path, value))

        # Preserve order but remove duplicates.
        unique = []
        seen = set()
        for path in candidates:
            key = os.path.normcase(path)
            if key not in seen:
                seen.add(key)
                unique.append(path)
        return unique

    def create_project(self, project: str, description: str = "", tech_stack: str = ""):
        with Session(self.engine) as session:
            project_state = Projects(
                project=project,
                description=description or "",
                tech_stack=tech_stack or "",
                created_at=datetime.utcnow().isoformat(timespec="seconds"),
                message_stack_json=json.dumps([]),
            )
            session.add(project_state)
            session.commit()

    def delete_project(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                session.delete(project_state)
                session.commit()

    def add_message_to_project(self, project: str, message: dict):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                message_stack.append(message)
                project_state.message_stack_json = json.dumps(message_stack)
                session.commit()
            else:
                message_stack = [message]
                project_state = Projects(project=project, message_stack_json=json.dumps(message_stack))
                session.add(project_state)
                session.commit()

    def add_message_from_imposter(self, project: str, message: str):
        new_message = self.new_message()
        new_message["message"] = message
        emit_agent("server-message", {"messages": new_message})
        self.add_message_to_project(project, new_message)

    def add_message_from_user(self, project: str, message: str):
        new_message = self.new_message()
        new_message["message"] = message
        new_message["from_imposter"] = False
        emit_agent("server-message", {"messages": new_message})
        self.add_message_to_project(project, new_message)

    def get_messages(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                return json.loads(project_state.message_stack_json)
            return None

    def get_latest_message_from_user(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in reversed(message_stack):
                    if not message["from_imposter"]:
                        return message
            return None

    def validate_last_message_is_from_user(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                if message_stack:
                    return not message_stack[-1]["from_imposter"]
            return False

    def get_latest_message_from_imposter(self, project: str):
        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in reversed(message_stack):
                    if message["from_imposter"]:
                        return message
            return None

    def get_project_list(self):
        with Session(self.engine) as session:
            projects = session.query(Projects).all()
            unique_projects = []
            seen = set()
            for project in projects:
                display_name = (project.project or "").strip()
                key = self._canonical_name(display_name)
                if key and key not in seen:
                    seen.add(key)
                    unique_projects.append(display_name)
            return unique_projects

    def get_project_details(self):
        with Session(self.engine) as session:
            projects = session.query(Projects).all()
            unique_projects = []
            seen = set()

            for project in projects:
                display_name = (project.project or "").strip()
                key = self._canonical_name(display_name)
                if key and key not in seen:
                    seen.add(key)
                    unique_projects.append(
                        {
                            "project": display_name,
                            "description": (project.description or "").strip(),
                            "tech_stack": (project.tech_stack or "").strip(),
                            "created_at": (project.created_at or "").strip(),
                        }
                    )

            return unique_projects

    def get_all_messages_formatted(self, project: str):
        formatted_messages = []

        with Session(self.engine) as session:
            project_state = session.query(Projects).filter(Projects.project == project).first()
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in message_stack:
                    if message["from_imposter"]:
                        formatted_messages.append(f"Imposter 101: {message['message']}")
                    else:
                        formatted_messages.append(f"User: {message['message']}")

            return formatted_messages

    def get_project_path(self, project: str):
        candidates = self._project_path_candidates(project)

        for path in candidates:
            if os.path.isdir(path):
                return path

        # Fallback: match existing directories by canonical name.
        canonical = self._canonical_name(project)
        if canonical and os.path.isdir(self.project_path):
            matching = []
            for name in os.listdir(self.project_path):
                full_path = os.path.join(self.project_path, name)
                if os.path.isdir(full_path) and self._canonical_name(name) == canonical:
                    matching.append(full_path)

            if matching:
                matching.sort(key=lambda p: len(os.path.basename(p)))
                return matching[0]

        # Default to first normalized candidate for new projects.
        return candidates[0] if candidates else self.project_path

    def project_to_zip(self, project: str):
        project_path = self.get_project_path(project)
        zip_path = f"{project_path}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), os.path.join(project_path, '..'))
                    zipf.write(os.path.join(root, file), arcname=relative_path)

        return zip_path

    def get_zip_path(self, project: str):
        return f"{self.get_project_path(project)}.zip"
    
    def get_project_files(self, project_name: str):
        if not project_name:
            return []

        base_path = os.path.abspath(self.project_path)
        directory = os.path.abspath(self.get_project_path(project_name))

        # Ensure the directory is within the allowed base path.
        if not os.path.exists(directory) or os.path.commonpath([directory, base_path]) != base_path:
            return []

        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                file_relative_path = os.path.relpath(root, directory)
                if file_relative_path == '.':
                    file_relative_path = ''
                file_path = os.path.join(file_relative_path, filename)
                try:
                    with open(os.path.join(root, filename), 'r') as file:
                        files.append({
                            "file": file_path,
                            "code": file.read()
                        })
                except Exception as e:
                    print(f"Error reading file {filename}: {e}")
        return files
