<script lang="ts">
  import AuthGuard from '$lib/components/AuthGuard.svelte'

  export let requireAuth = true
  export let redirectTo = '/'
  export let content = 'Content'
</script>

<AuthGuard {requireAuth} {redirectTo}>
  <div data-testid="content">{content}</div>
</AuthGuard>
