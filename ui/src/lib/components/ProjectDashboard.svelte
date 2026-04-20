<script>
  import { projectDetails, selectedProject, tokenUsage, messages, agentState, isSending } from "$lib/store";
  import { createProject, fetchInitialData, deleteProject, fetchMessages, fetchAgentState, fetchProjectFiles } from "$lib/api";

  let projectName = "";
  let projectDescription = "";
  let projectTechStack = "";
  let isCreating = false;

  async function createNewProject() {
    if (!projectName.trim()) {
      return;
    }

    isCreating = true;
    try {
      await createProject(projectName.trim(), projectDescription.trim(), projectTechStack.trim());
      await selectProject(projectName.trim());
      projectName = "";
      projectDescription = "";
      projectTechStack = "";
    } finally {
      isCreating = false;
    }
  }

  async function selectProject(project) {
    $selectedProject = project;
    await fetchMessages();
    await fetchAgentState();
    await fetchProjectFiles(project);
  }

  async function removeProject(project) {
    if (!confirm(`Are you sure you want to delete ${project}?`)) {
      return;
    }

    await deleteProject(project);
    await fetchInitialData();
    if ($selectedProject === project) {
      $selectedProject = "select project";
      messages.set([]);
      agentState.set(null);
      tokenUsage.set(0);
      isSending.set(false);
    }
  }
</script>

<section class="dashboard-shell">
  <div class="dashboard-header">
    <div>
      <p class="eyebrow">Project dashboard</p>
      <h2>Build, iterate, and deploy from one place</h2>
      <p class="subtle">Create a project, describe the stack, and jump straight into the workspace.</p>
    </div>
  </div>

  <div class="create-card">
    <div class="input-grid">
      <input bind:value={projectName} placeholder="Project name" class="field" />
      <input bind:value={projectDescription} placeholder="Description" class="field" />
      <input bind:value={projectTechStack} placeholder="Tech stack" class="field" />
      <button class="create-button" on:click|preventDefault={createNewProject} disabled={isCreating}>
        {isCreating ? "Creating..." : "Create project"}
      </button>
    </div>
  </div>

  <div class="project-grid">
    {#each $projectDetails as project}
      <article class:selected={$selectedProject === project.project} class="project-card">
        <div class="project-card-top">
          <div>
            <h3>{project.project}</h3>
            <p>{project.description || "No description yet."}</p>
          </div>
          <button class="delete-button" on:click|preventDefault={() => removeProject(project.project)} aria-label="Delete project">
            Delete
          </button>
        </div>

        <dl>
          <div>
            <dt>Tech stack</dt>
            <dd>{project.tech_stack || "Not specified"}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{project.created_at || "Unknown"}</dd>
          </div>
        </dl>

        <div class="actions">
          <button class="open-button" on:click|preventDefault={() => selectProject(project.project)}>Open project</button>
        </div>
      </article>
    {/each}
  </div>
</section>

<style>
  .dashboard-shell {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0.5rem 0 0.75rem;
  }

  .dashboard-header h2 {
    margin: 0.25rem 0 0;
    font-size: 1.35rem;
  }

  .eyebrow {
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    color: #8ea0b8;
  }

  .subtle {
    margin: 0.35rem 0 0;
    color: #9aa7b8;
    font-size: 0.92rem;
  }

  .create-card {
    padding: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    background: rgba(18, 21, 28, 0.8);
    backdrop-filter: blur(10px);
  }

  .input-grid {
    display: grid;
    grid-template-columns: 1.2fr 1.4fr 1fr auto;
    gap: 0.75rem;
  }

  .field {
    min-width: 0;
    padding: 0.8rem 0.9rem;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: #0b1220;
    color: #e5eefc;
  }

  .create-button,
  .open-button,
  .delete-button {
    border: 0;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .create-button {
    padding: 0.8rem 1rem;
    background: linear-gradient(180deg, #2f80ed, #1f5fbe);
    color: white;
  }

  .project-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 0.9rem;
  }

  .project-card {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    padding: 1rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(13, 17, 24, 0.9);
  }

  .project-card.selected {
    outline: 2px solid rgba(47, 128, 237, 0.6);
  }

  .project-card-top {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .project-card h3,
  .project-card p,
  .project-card dd,
  .project-card dt {
    margin: 0;
  }

  .project-card p,
  .project-card dd {
    color: #a6b3c8;
    font-size: 0.9rem;
  }

  dl {
    display: grid;
    gap: 0.6rem;
  }

  dt {
    color: #74849c;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
  }

  .open-button {
    padding: 0.7rem 0.9rem;
    background: rgba(47, 128, 237, 0.16);
    color: #dcecff;
  }

  .delete-button {
    padding: 0.55rem 0.7rem;
    background: rgba(239, 68, 68, 0.12);
    color: #ffb4b4;
    align-self: flex-start;
  }

  @media (max-width: 1100px) {
    .input-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  @media (max-width: 700px) {
    .input-grid {
      grid-template-columns: 1fr;
    }
  }
</style>