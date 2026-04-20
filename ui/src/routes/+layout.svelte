<script>
  import Sidebar from "$lib/components/Sidebar.svelte";
  import { Toaster } from "$lib/components/ui/sonner";
  import { ModeWatcher } from "mode-watcher";
  import "../app.pcss";
</script>

<main>
  <div class="h-dvh w-full flex overflow-hidden">
      <Toaster richColors/>
      <ModeWatcher />
      <Sidebar />
      <div class="min-w-0 flex-1 overflow-y-auto">
        <slot />
      </div>
  </div>
</main>
