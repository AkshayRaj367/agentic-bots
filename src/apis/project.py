from flask import blueprints, request, jsonify, send_file, make_response, send_from_directory
from werkzeug.utils import secure_filename
from src.logger import Logger, route_logger
from src.config import Config
from src.project import ProjectManager
from src.services import Tunnel
from ..state import AgentState

import os
import mimetypes

project_bp = blueprints.Blueprint("project", __name__)

logger = Logger()
manager = ProjectManager()


PREVIEW_ENTRY_CANDIDATES = [
    "index.html",
    "dist/index.html",
    "build/index.html",
    "public/index.html",
    "src/index.html",
]


def _resolve_preview_entry(project_path: str):
    for candidate in PREVIEW_ENTRY_CANDIDATES:
        file_path = os.path.join(project_path, candidate)
        if os.path.isfile(file_path):
            return candidate

    # Fallback: generated files can occasionally include wrapping punctuation
    # in names (for example, `index.html`) or be nested in subfolders.
    html_candidates = []
    generic_html_candidates = []
    for root, _, files in os.walk(project_path):
        for file_name in files:
            normalized_name = file_name.strip().strip("`'\"").lower()
            if normalized_name in {"index.html", "index.htm", "home.html", "main.html"}:
                rel_path = os.path.relpath(os.path.join(root, file_name), project_path)
                depth = rel_path.count(os.sep)
                html_candidates.append((depth, rel_path))
            elif normalized_name.endswith(".html") or normalized_name.endswith(".htm"):
                rel_path = os.path.relpath(os.path.join(root, file_name), project_path)
                depth = rel_path.count(os.sep)
                generic_html_candidates.append((depth, rel_path))

    if html_candidates:
        html_candidates.sort(key=lambda item: (item[0], len(item[1])))
        return html_candidates[0][1]

    if generic_html_candidates:
        generic_html_candidates.sort(key=lambda item: (item[0], len(item[1])))
        return generic_html_candidates[0][1]

    return None


# Project APIs

@project_bp.route("/api/get-project-files", methods=["GET"])
@route_logger(logger)
def project_files():
    project_name = secure_filename(request.args.get("project_name"))
    files = manager.get_project_files(project_name)  
    return jsonify({"files": files})


@project_bp.route("/api/project-preview-url", methods=["GET"])
@route_logger(logger)
def project_preview_url():
    project_name = secure_filename(request.args.get("project_name", ""))
    if not project_name:
        return jsonify({"preview_url": None})

    project_path = manager.get_project_path(project_name)
    preview_entry = _resolve_preview_entry(project_path)
    if not preview_entry:
        return jsonify({"preview_url": None})

    encoded_project_name = secure_filename(project_name)
    preview_url = f"/api/project-preview/{encoded_project_name}/{preview_entry}"
    return jsonify({"preview_url": preview_url})


@project_bp.route("/api/project-preview/<project_name>", methods=["GET"])
@project_bp.route("/api/project-preview/<project_name>/", defaults={"asset_path": ""}, methods=["GET"])
@project_bp.route("/api/project-preview/<project_name>/<path:asset_path>", methods=["GET"])
@route_logger(logger)
def project_preview(project_name: str, asset_path: str = ""):
    safe_project_name = secure_filename(project_name)
    project_path = manager.get_project_path(safe_project_name)

    if not os.path.isdir(project_path):
        return jsonify({"error": "Project not found"}), 404

    resolved_asset_path = asset_path
    if not resolved_asset_path:
        preview_entry = _resolve_preview_entry(project_path)
        if not preview_entry:
            return jsonify({"error": "No previewable entry file found"}), 404
        resolved_asset_path = preview_entry

    normalized_path = os.path.normpath(resolved_asset_path)
    absolute_file_path = os.path.abspath(os.path.join(project_path, normalized_path))
    absolute_project_path = os.path.abspath(project_path)

    if not absolute_file_path.startswith(absolute_project_path):
        return jsonify({"error": "Invalid preview path"}), 400

    if os.path.isdir(absolute_file_path):
        absolute_file_path = os.path.join(absolute_file_path, "index.html")

    if not os.path.exists(absolute_file_path):
        return jsonify({"error": "Preview file not found"}), 404

    # Some generated files may include wrapper punctuation in names (e.g. `index.html`),
    # which confuses default content-type detection. Normalize before guessing MIME type.
    display_name = os.path.basename(absolute_file_path).strip().strip("`'\"")
    guessed_mimetype, _ = mimetypes.guess_type(display_name)

    if guessed_mimetype:
        return send_file(absolute_file_path, mimetype=guessed_mimetype, as_attachment=False)

    relative_file_path = os.path.relpath(absolute_file_path, absolute_project_path)
    return send_from_directory(absolute_project_path, relative_file_path)

@project_bp.route("/api/create-project", methods=["POST"])
@route_logger(logger)
def create_project():
    data = request.json
    project_name = data.get("project_name")
    description = data.get("description", "")
    tech_stack = data.get("tech_stack", "")
    manager.create_project(secure_filename(project_name), description=description, tech_stack=tech_stack)
    return jsonify({"message": "Project created"})


@project_bp.route("/api/projects", methods=["GET"])
@route_logger(logger)
def projects():
    return jsonify({"projects": manager.get_project_details()})


@project_bp.route("/api/delete-project", methods=["POST"])
@route_logger(logger)
def delete_project():
    data = request.json
    project_name = secure_filename(data.get("project_name"))
    manager.delete_project(project_name)
    AgentState().delete_state(project_name)
    return jsonify({"message": "Project deleted"})


@project_bp.route("/api/download-project", methods=["GET"])
@route_logger(logger)
def download_project():
    project_name = secure_filename(request.args.get("project_name"))
    manager.project_to_zip(project_name)
    project_path = manager.get_zip_path(project_name)
    return send_file(project_path, as_attachment=False)


@project_bp.route("/api/download-project-pdf", methods=["GET"])
@route_logger(logger)
def download_project_pdf():
    project_name = secure_filename(request.args.get("project_name"))
    pdf_dir = Config().get_pdfs_dir()
    pdf_path = os.path.join(pdf_dir, f"{project_name}.pdf")

    response = make_response(send_file(pdf_path))
    response.headers['Content-Type'] = 'project_bplication/pdf'
    return response


@project_bp.route("/api/deploy-project", methods=["POST"])
@route_logger(logger)
def deploy_project():
    data = request.json or {}
    project_name = secure_filename(data.get("project_name", ""))

    if not project_name:
        response = jsonify({"error": "Project name is required"})
        response.status_code = 400
        return response

    deploy_metadata = Tunnel().deploy(project_name)
    if isinstance(deploy_metadata, dict) and deploy_metadata.get("error"):
        response = jsonify(deploy_metadata)
        response.status_code = 500
        return response

    deploy_url = deploy_metadata.get("deploy_url") if isinstance(deploy_metadata, dict) else None

    return jsonify({"deploy_url": deploy_url, "raw": deploy_metadata})
