<script lang="ts">
  import { LoadingSpinner, Button, PageHeader, StatusBadge, EmptyState } from '$lib/components'
  
  // We need a description at the very least.
  interface Range {
    id: string
    name: string
    description: string
    isRunning: boolean
    state?: 'on' | 'off' | 'starting' | 'stopping'
    created_at?: string
    updated_at?: string
  }

  export let searchTerm: string
  export let deployedRanges: Range[]
  export let isLoading: boolean = false
  export let error: string = ''
</script>

<div class="flex flex-1 flex-wrap content-start p-4">
  <PageHeader 
    title="Ranges"
    searchPlaceholder="Search Ranges"
    bind:searchValue={searchTerm}
  >
    <svelte:fragment slot="actions">
      <Button href="/blueprints" variant="primary" class="w-full sm:w-auto whitespace-nowrap">
        Create range
      </Button>
    </svelte:fragment>
  </PageHeader>

  <div class="flex flex-1 flex-wrap content-start p-4 pl-0">
    {#if isLoading}
      <div class="flex w-full items-center justify-center p-20">
        <LoadingSpinner size="lg" />
      </div>
    {:else if error}
      <div class="w-full p-4">
        <div
          class="rounded border-l-4 border-amber-500 bg-amber-50 p-4 text-amber-700 shadow-md"
          role="alert"
        >
          <p class="mb-2 font-bold">We couldn't load your ranges</p>
          <p class="mb-3">{error}</p>
          <p class="text-sm">
            Showing sample data instead. You can still explore the interface.
          </p>
        </div>
      </div>
    {:else if deployedRanges.length === 0}
      <EmptyState
        title="Ready to get started?"
        description="You don't have any cyber ranges yet. Create your first range to start building your lab environment!"
        iconType="range"
        actionLabel="Create your first range"
        on:action={() => window.location.href = '/blueprints'}
      />
    {:else}
      {#each deployedRanges.filter((post) => post.name
          .toLowerCase()
          .includes(searchTerm.toLowerCase()) || post.description
          .toLowerCase()
          .includes(searchTerm.toLowerCase())) as post}
        <div
          class="m-4 flex h-60 w-80 flex-col justify-between rounded-lg border border-gray-300 bg-white p-4 pb-5 shadow-sm"
        >
          <div>
            <!-- Status badge and name -->
            <div class="mb-3 flex items-start justify-between">
              <h2 class="line-clamp-2 max-w-[70%] text-lg font-bold" title={post.name}>
                {post.name}
              </h2>
              <StatusBadge 
                variant={
                  post.state === 'starting' ? 'warning' :
                  post.state === 'on' ? 'success' :
                  post.state === 'stopping' ? 'warning' :
                  'gray'
                }
                size="sm"
              >
                {#if post.state === 'starting'}
                  Deploying
                {:else if post.state === 'on'}
                  Started
                {:else if post.state === 'stopping'}
                  Stopping
                {:else if post.state === 'off'}
                  Stopped
                {:else}
                  {post.isRunning ? 'Started' : 'Stopped'}
                {/if}
              </StatusBadge>
            </div>

            <!-- Description -->
            <p class="mb-4 line-clamp-2 text-sm text-gray-700">
              {post.description}
            </p>
          </div>

          <div>
            <!-- Created date -->
            <div class="mb-4 text-xs text-gray-500">
              {#if post.created_at}
                Created: {new Date(post.created_at).toLocaleDateString()}
              {:else}
                Recently created
              {/if}
            </div>

            <!-- Action buttons -->
            <div class="flex justify-between">
              <Button 
                href={`/ranges/${post.id}`}
                variant="primary"
                size="sm"
              >
                Manage
              </Button>
              <Button 
                variant={post.isRunning ? 'danger' : 'success'}
                size="sm"
              >
                {post.isRunning ? 'Stop' : 'Start'}
              </Button>
            </div>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>