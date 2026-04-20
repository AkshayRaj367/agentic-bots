<script>
  import { get } from "svelte/store";
  import { onDestroy } from "svelte";
  import { toast } from "svelte-sonner";
  import { agentState } from "$lib/store";
  import { selectedProject, isSending } from "$lib/store";
  import { API_BASE_URL, socket, getProjectPreviewUrl, fetchProjectFiles } from "$lib/api";

  export let showDeployControls = true;

  let previewUrl = null;
  let activeView = "preview";
  let currentProject = get(selectedProject);
  let pendingGeneration = false;
  let completionHandled = false;
  let autoOpenBrowserOnComplete = false;
  let previewNotice = "";
  let deployUrl = null;
  let deployStatus = "";
  let isDeploying = false;

  function normalizeFilename(filePath) {
    const name = (filePath || "").split("/").pop();
    return (name || "").trim().replace(/^[`'\"]+|[`'\"]+$/g, "").toLowerCase();
  }

  async function buildNoPreviewNotice(projectName) {
    try {
      const files = await fetchProjectFiles(projectName);
      if (!files || files.length === 0) {
        return "No files were generated yet for this project.";
      }

      const names = files.map((f) => normalizeFilename(f.file));
      const hasHtml = names.some((name) => name.endsWith(".html") || name.endsWith(".htm"));
      if (hasHtml) {
        return "No preview entry was detected yet. Try View in app again in a few seconds.";
      }

      const extensions = names
        .map((name) => {
          const index = name.lastIndexOf(".");
          return index >= 0 ? name.slice(index) : "(no extension)";
        })
        .filter(Boolean);

      const uniqueExtensions = [...new Set(extensions)].slice(0, 3).join(", ");
      return `This project does not contain an HTML entry file for browser preview. Detected file types: ${uniqueExtensions}.`;
    } catch {
      return "No browser preview is available for this project yet.";
    }
  }

  async function loadPreviewUrl(projectName) {
    if (!projectName || projectName.toLowerCase().includes("select")) {
      previewUrl = null;
      previewNotice = "";
      deployUrl = null;
      deployStatus = "";
      if (activeView === "preview") {
        activeView = "screenshot";
      }
      return;
    }

    try {
      previewUrl = await getProjectPreviewUrl(projectName);
      deployUrl = null;
      deployStatus = "";
      if (previewUrl) {
        activeView = "preview";
        previewNotice = "";
      } else if (activeView === "preview") {
        activeView = "screenshot";
      }
    } catch {
      previewUrl = null;
      if (activeView === "preview") {
        activeView = "screenshot";
      }
    }
  }

  const unsubscribeProject = selectedProject.subscribe(async (projectName) => {
    currentProject = projectName;
    await loadPreviewUrl(projectName);
  });

  async function handleGenerationComplete() {
    const currentProject = get(selectedProject);
    await loadPreviewUrl(currentProject);

    if (!previewUrl) {
      previewNotice = await buildNoPreviewNotice(currentProject);
      toast.info(previewNotice);
      return;
    }

    activeView = "preview";
    toast.success("Generated app is ready. Use View in app or Open browser.");

    if (autoOpenBrowserOnComplete) {
      const opened = openPreviewInNewTab();
      if (!opened) {
        toast.warning("Preview popup was blocked. Click Open browser to launch it.");
      }
    }
  }

  const unsubscribeSending = isSending.subscribe(async (sending) => {
    if (sending) {
      pendingGeneration = true;
      completionHandled = false;
      return;
    }

    if (pendingGeneration && !completionHandled) {
      completionHandled = true;
      pendingGeneration = false;
      await handleGenerationComplete();
    }
  });

  onDestroy(() => {
    unsubscribeProject();
    unsubscribeSending();
    socket.off("screenshot", handleScreenshot);
  });

  function openPreviewInNewTab() {
    if (!previewUrl) return false;
    const opened = window.open(`${API_BASE_URL}${previewUrl}`, "_blank", "noopener,noreferrer");
    return Boolean(opened);
  }

  function viewPreviewInApp() {
    if (!previewUrl) return;
    activeView = "preview";
  }

  async function deployProject() {
    const projectName = get(selectedProject);
    if (!projectName || projectName.toLowerCase().includes("select")) {
      toast.error("Select a project first.");
      return;
    }

    if (!confirm("Start a temporary tunnel deployment for this project?")) {
      return;
    }

    isDeploying = true;
    deployStatus = "Starting temporary tunnel...";

    try {
      const response = await fetch(`${API_BASE_URL}/api/deploy-project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_name: projectName }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.details || data.error || "Unable to start temporary tunnel deployment.");
      }

      deployUrl = data.deploy_url || null;
      deployStatus = deployUrl
        ? "Temporary deployment is live."
        : "Tunnel started, but no public URL was returned.";

      if (deployUrl) {
        toast.success("Temporary tunnel started.");
      } else {
        toast.warning(deployStatus);
      }
    } catch (error) {
      deployStatus = `Deployment failed: ${error.message}`;
      toast.error(deployStatus);
    } finally {
      isDeploying = false;
    }
  }

  function handleScreenshot(msg) {
    const data = msg["data"];
    const img = document.querySelector(".browser-img");
    if (img) {
      img.src = `data:image/png;base64,${data}`;
    }
  }

  loadPreviewUrl(get(selectedProject));
  socket.on("screenshot", handleScreenshot);

</script>

<div class="w-full h-full flex flex-col border-[3px] rounded-xl overflow-y-auto bg-browser-window-background border-window-outline">
  <div class="p-2 flex items-center border-b border-border bg-browser-window-ribbon h-12">
    <div class="flex space-x-2 ml-2 mr-4">
      <div class="w-3 h-3 bg-browser-window-dots rounded-full"></div>
      <div class="w-3 h-3 bg-browser-window-dots rounded-full"></div>
      <div class="w-3 h-3 bg-browser-window-dots rounded-full"></div>
    </div>
    <input
      type="text"
      id="browser-url"
      class="flex-grow h-7 text-xs rounded-lg p-2 overflow-x-auto bg-browser-window-search text-browser-window-foreground"
      placeholder="imposter://newtab"
      value={activeView === "preview" && previewUrl ? `${API_BASE_URL}${previewUrl}` : ($agentState?.browser_session.url || "")}
    />
    {#if previewUrl}
      <button
        class="ml-2 h-7 px-2 text-xs rounded-md bg-secondary text-foreground"
        on:click={viewPreviewInApp}
      >
        view in app
      </button>
    {/if}
    {#if previewUrl}
      <button
        class="ml-2 h-7 px-2 text-xs rounded-md bg-secondary text-foreground"
        on:click={openPreviewInNewTab}
      >
        open browser
      </button>
    {/if}
  </div>
  {#if currentProject && !currentProject.toLowerCase().includes("select")}
    <div class="px-2 py-1 flex items-center gap-2 border-b border-border bg-browser-window-ribbon">
      <button
        class="text-xs px-2 py-1 rounded-md"
        class:bg-secondary={activeView === "preview"}
        on:click={() => (activeView = "preview")}
      >
        live preview
      </button>
      <button
        class="text-xs px-2 py-1 rounded-md"
        class:bg-secondary={activeView === "screenshot"}
        on:click={() => (activeView = "screenshot")}
      >
        agent screenshot
      </button>
      {#if showDeployControls}
        <button
          class="text-xs px-2 py-1 rounded-md"
          class:bg-secondary={activeView === "deploy"}
          on:click={() => (activeView = "deploy")}
        >
          deploy
        </button>
      {/if}
      <label class="ml-auto flex items-center gap-1 text-xs text-foreground/80">
        <input
          type="checkbox"
          bind:checked={autoOpenBrowserOnComplete}
        />
        auto-open browser on complete
      </label>
    </div>
  {/if}
  <div id="browser-content" class="flex-grow overflow-y-auto">
    {#if activeView === "preview" && previewUrl}
      <iframe
        title="Project preview"
        class="preview-frame"
        src={`${API_BASE_URL}${previewUrl}`}
      ></iframe>
    {:else if showDeployControls && activeView === "deploy"}
      <div class="deploy-panel">
        <h3>Create a temporary tunnel deploy?</h3>
        <p>Uses a project-name subdomain for short-term public access.</p>
        <button class="deploy-button" on:click={deployProject} disabled={isDeploying}>
          {isDeploying ? "Starting tunnel..." : "Start temporary deploy"}
        </button>
        {#if deployStatus}
          <p class="deploy-status">{deployStatus}</p>
        {/if}
        {#if deployUrl}
          <a class="deploy-link" href={deployUrl} target="_blank" rel="noreferrer">
            {deployUrl}
          </a>
        {/if}
      </div>
    {:else if showDeployControls && activeView === "deploy" && !currentProject}
      <div class="deploy-panel">
        <h3>Select a project first</h3>
        <p>Use the dashboard or project selector to choose a project before deploying.</p>
      </div>
    {:else if previewNotice}
      <div class="text-gray-400 text-sm text-center mt-5 px-4">{previewNotice}</div>
    {:else if $agentState?.browser_session.screenshot}
      <img
        class="browser-img"
        src={API_BASE_URL + "/api/get-browser-snapshot?snapshot_path=" + $agentState?.browser_session.screenshot}
        alt="Browser snapshot"
      />
    {:else}
      <div class="text-gray-400 text-sm text-center mt-5"><strong>💡 TIP:</strong> You can include a Git URL in your prompt to clone a repo!</div>
    {/if}
  </div>
</div>

<style>
  #browser-url {
    pointer-events: none
  }

  .browser-img {
    display: block;
    object-fit: contain;
  }

  .preview-frame {
    width: 100%;
    height: 100%;
    border: 0;
    background: white;
  }

  .deploy-panel {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    height: 100%;
    padding: 1.25rem;
    color: #dbe7ff;
  }

  .deploy-panel h3 {
    margin: 0;
    font-size: 1.1rem;
  }

  .deploy-panel p {
    margin: 0;
    color: #9fb0c9;
  }

  .deploy-button {
    width: fit-content;
    padding: 0.75rem 1rem;
    border: 0;
    border-radius: 12px;
    background: linear-gradient(180deg, #2f80ed, #1f5fbe);
    color: white;
    font-weight: 700;
    cursor: pointer;
  }

  .deploy-button:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }

  .deploy-status {
    font-size: 0.92rem;
    color: #cfe0ff;
  }

  .deploy-link {
    word-break: break-all;
    color: #7fb3ff;
    text-decoration: underline;
  }
</style>