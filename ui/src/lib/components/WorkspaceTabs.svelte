<script>
  import { Tabs, TabsContent, TabsList, TabsTrigger } from "$lib/components/ui/tabs/index.js";
  import EditorWidget from "$lib/components/EditorWidget.svelte";
  import BrowserWidget from "$lib/components/BrowserWidget.svelte";
  import TerminalWidget from "$lib/components/TerminalWidget.svelte";
  import MessageContainer from "$lib/components/MessageContainer.svelte";
  import MessageInput from "$lib/components/MessageInput.svelte";
  import DeployPanel from "$lib/components/DeployPanel.svelte";
  import { selectedProject } from "$lib/store";
</script>

<section class="workspace-shell">
  <Tabs value="editor" class="tabs-root">
    <TabsList class="workspace-tabs-list">
      <TabsTrigger value="editor">Editor</TabsTrigger>
      <TabsTrigger value="deploy">Deploy</TabsTrigger>
    </TabsList>

    <TabsContent value="editor" class="workspace-content">
      <div class="workspace-grid">
        <div class="editor-pane">
          <EditorWidget />
        </div>

        <div class="preview-pane">
          <BrowserWidget showDeployControls={false} />
          <TerminalWidget />
        </div>
      </div>

      <div class="chat-pane">
        <MessageContainer />
        <MessageInput />
      </div>
    </TabsContent>

    <TabsContent value="deploy" class="workspace-content">
      <div class="deploy-wrapper">
        {#if $selectedProject && !$selectedProject.toLowerCase().includes("select")}
          <DeployPanel />
        {:else}
          <div class="empty-state">
            <h3>Select a project first</h3>
            <p>The Deploy tab is available after you choose or create a project.</p>
          </div>
        {/if}
      </div>
    </TabsContent>
  </Tabs>
</section>

<style>
  .workspace-shell {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .tabs-root {
    width: 100%;
  }

  .workspace-tabs-list {
    margin-bottom: 0.75rem;
  }

  .workspace-content {
    margin-left: 0;
  }

  .workspace-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(380px, 1fr);
    gap: 1rem;
    align-items: stretch;
  }

  .editor-pane,
  .preview-pane,
  .chat-pane,
  .deploy-wrapper {
    min-width: 0;
  }

  .preview-pane {
    display: grid;
    grid-template-rows: minmax(360px, 1fr) minmax(220px, 280px);
    gap: 1rem;
  }

  .chat-pane {
    margin-top: 1rem;
    display: grid;
    grid-template-rows: minmax(280px, 1fr) auto;
    gap: 0.75rem;
  }

  .empty-state {
    padding: 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(13, 17, 24, 0.9);
  }

  .empty-state h3,
  .empty-state p {
    margin: 0;
  }

  .empty-state p {
    margin-top: 0.4rem;
    color: #9aa7b8;
  }

  @media (max-width: 1200px) {
    .workspace-grid {
      grid-template-columns: 1fr;
    }

    .preview-pane {
      grid-template-rows: minmax(300px, 1fr) minmax(220px, 280px);
    }
  }
</style>