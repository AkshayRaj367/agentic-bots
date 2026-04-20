import {
  agentState,
  internet,
  modelList,
  projectList,
  projectDetails,
  messages,
  projectFiles,
  searchEngineList,
  selectedModel,
} from "./store";
import { io } from "socket.io-client";


const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://127.0.0.1:1337';
    } else {
      return `http://${host}:1337`;
    }
  } else {
    return 'http://127.0.0.1:1337';
  }
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getApiBaseUrl();
export const socket = io(API_BASE_URL, { autoConnect: false });

function getAllModelNames(models) {
  return Object.values(models || {})
    .flat()
    .map((entry) => entry?.[0])
    .filter(Boolean);
}

export function getPreferredModel(models = null) {
  const sourceModels = models || JSON.parse(localStorage.getItem("defaultData") || "{}").models || {};
  const availableModels = getAllModelNames(sourceModels);
  const storedModel = localStorage.getItem("selectedModel");

  if (storedModel && availableModels.includes(storedModel)) {
    return storedModel;
  }

  return availableModels[0] || "";
}

export function ensurePreferredModel(models = null) {
  const preferredModel = getPreferredModel(models);
  if (preferredModel) {
    selectedModel.set(preferredModel);
    localStorage.setItem("selectedModel", preferredModel);
  }
  return preferredModel;
}

export async function checkServerStatus() {
  try{await fetch(`${API_BASE_URL}/api/status`) ; return true;}
  catch (error) {
    return false;
  }

}

export async function fetchInitialData() {
  const response = await fetch(`${API_BASE_URL}/api/data`);
  const data = await response.json();
  projectList.set(data.projects);
  projectDetails.set(data.project_details || []);
  modelList.set(data.models);
  searchEngineList.set(data.search_engines);
  localStorage.setItem("defaultData", JSON.stringify(data));
  ensurePreferredModel(data.models);
}

export async function createProject(projectName, description = "", techStack = "") {
  await fetch(`${API_BASE_URL}/api/create-project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      project_name: projectName,
      description,
      tech_stack: techStack,
    }),
  });
  projectList.update((projects) => [...projects, projectName]);
  await fetchInitialData();
}

export async function deleteProject(projectName) {
  await fetch(`${API_BASE_URL}/api/delete-project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
  await fetchInitialData();
}

export async function fetchProjectDetails() {
  const response = await fetch(`${API_BASE_URL}/api/projects`);
  const data = await response.json();
  projectDetails.set(data.projects || []);
  return data.projects || [];
}

export async function fetchMessages() {
  const projectName = localStorage.getItem("selectedProject");
  const response = await fetch(`${API_BASE_URL}/api/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
  const data = await response.json();
  messages.set(data.messages);
}

export async function fetchAgentState() {
  const projectName = localStorage.getItem("selectedProject");
  const response = await fetch(`${API_BASE_URL}/api/get-agent-state`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
  const data = await response.json();
  agentState.set(data.state);
}

export async function executeAgent(prompt) {
  const projectName = localStorage.getItem("selectedProject");
  const modelId = ensurePreferredModel();

  if (!modelId) {
    alert("Please select the LLM model first.");
    return;
  }

  await fetch(`${API_BASE_URL}/api/execute-agent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      prompt: prompt,
      base_model: modelId,
      project_name: projectName,
    }),
  });

  await fetchMessages();
}

export async function getBrowserSnapshot(snapshotPath) {
  const response = await fetch(`${API_BASE_URL}/api/browser-snapshot`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ snapshot_path: snapshotPath }),
  });
  const data = await response.json();
  return data.snapshot;
}

export async function fetchProjectFiles(projectName = null) {
  const resolvedProjectName = projectName || localStorage.getItem("selectedProject");
  const response = await fetch(
    `${API_BASE_URL}/api/get-project-files?project_name=${encodeURIComponent(resolvedProjectName || "")}`
  );
  const data = await response.json();
  projectFiles.set(data.files);
  return data.files;
}

export async function checkInternetStatus() {
  if (navigator.onLine) {
    internet.set(true);
  } else {
    internet.set(false);
  }
}

export async function fetchSettings() {
  const response = await fetch(`${API_BASE_URL}/api/settings`);
  const data = await response.json();
  return data.settings;
}

export async function updateSettings(settings) {
  await fetch(`${API_BASE_URL}/api/settings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });
}

export async function fetchLogs() {
  const response = await fetch(`${API_BASE_URL}/api/logs`);
  const data = await response.json();
  return data.logs;
}

export async function getProjectPreviewUrl(projectName) {
  const response = await fetch(
    `${API_BASE_URL}/api/project-preview-url?project_name=${encodeURIComponent(projectName)}`
  );
  const data = await response.json();
  return data.preview_url ? encodeURI(data.preview_url) : null;
}
