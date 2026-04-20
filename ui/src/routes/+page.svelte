<script>
  import { onDestroy, onMount } from "svelte";
  import { toast } from "svelte-sonner";

  import ControlPanel from "$lib/components/ControlPanel.svelte";
  import ProjectDashboard from "$lib/components/ProjectDashboard.svelte";
  import WorkspaceTabs from "$lib/components/WorkspaceTabs.svelte";

  import { serverStatus } from "$lib/store";
  import { initializeSockets, destroySockets } from "$lib/sockets";
  import { checkInternetStatus, checkServerStatus, fetchInitialData } from "$lib/api";

  let resizeEnabled =
    localStorage.getItem("resize") &&
    localStorage.getItem("resize") === "enable";

  onMount(() => {
    const load = async () => {
      await checkInternetStatus();

      if(!(await checkServerStatus())) {
        toast.error("Failed to connect to server");
        return;
      }
      serverStatus.set(true);
      await initializeSockets();
      await fetchInitialData();
    };
    load();
  });
  onDestroy(() => {
    destroySockets();
  });
</script>

<div class="flex min-h-full flex-col flex-1 gap-4 p-4 overflow-y-auto">
  <ProjectDashboard />
  <ControlPanel />
  <WorkspaceTabs />
</div>