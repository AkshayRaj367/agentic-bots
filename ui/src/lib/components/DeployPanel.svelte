<script>
  import { get } from "svelte/store";
  import { toast } from "svelte-sonner";
  import { selectedProject } from "$lib/store";
  import { API_BASE_URL } from "$lib/api";

  let isDeploying = false;
  let deployUrl = null;
  let deployStatus = "";

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
</script>

<section class="deploy-shell">
  <div class="hero">
    <p class="eyebrow">Deploy tab</p>
    <h3>Create a temporary tunnel deploy?</h3>
    <p class="subtle">Uses a project-name subdomain for short-term public access.</p>
  </div>

  <div class="card">
    <button class="deploy-button" on:click|preventDefault={deployProject} disabled={isDeploying}>
      {isDeploying ? "Starting tunnel..." : "Start temporary deploy"}
    </button>

    {#if deployStatus}
      <p class="status">{deployStatus}</p>
    {/if}

    {#if deployUrl}
      <a class="deploy-link" href={deployUrl} target="_blank" rel="noreferrer">
        {deployUrl}
      </a>
    {/if}
  </div>
</section>

<style>
  .deploy-shell {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0;
  }

  .hero h3,
  .hero p {
    margin: 0;
  }

  .hero h3 {
    font-size: 1.25rem;
    margin-top: 0.25rem;
  }

  .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    color: #8ea0b8;
  }

  .subtle {
    color: #9aa7b8;
    margin-top: 0.35rem;
  }

  .card {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    padding: 1rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(13, 17, 24, 0.9);
  }

  .deploy-button {
    width: fit-content;
    padding: 0.8rem 1rem;
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

  .status {
    margin: 0;
    color: #cfe0ff;
  }

  .deploy-link {
    word-break: break-all;
    color: #7fb3ff;
    text-decoration: underline;
  }
</style>