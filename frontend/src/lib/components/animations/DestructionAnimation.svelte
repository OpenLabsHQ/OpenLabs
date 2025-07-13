<script lang="ts">
  export let label: string = 'Removing resources'
</script>

<div class="flex flex-col items-center">
  <div class="destruction-container">
    <div class="building">
      <div class="building-block"></div>
      <div class="building-block"></div>
      <div class="building-block"></div>
      <div class="debris debris1"></div>
      <div class="debris debris2"></div>
      <div class="debris debris3"></div>
      <div class="debris debris4"></div>
    </div>
  </div>
  <p class="mt-2 text-sm font-medium text-red-700">{label}</p>
</div>

<style>
  /* Destruction animation */
  @keyframes building-shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-2px) rotate(-0.5deg); }
    75% { transform: translateX(2px) rotate(0.5deg); }
  }
  
  @keyframes debris-fall {
    0% {
      opacity: 0;
      transform: translateY(-10px) rotate(0deg);
    }
    20% {
      opacity: 1;
    }
    100% {
      opacity: 0;
      transform: translateY(60px) rotate(180deg);
    }
  }
  
  .destruction-container {
    position: relative;
    width: 80px;
    height: 100px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }
  
  .building {
    position: relative;
    animation: building-shake 3s infinite ease-in-out;
  }
  
  .building-block {
    width: 20px;
    height: 20px;
    background-color: var(--color-destroy-600);
    margin: 2px;
    opacity: 0.8;
    animation: building-shake 2s infinite ease-in-out;
  }
  
  .building-block:nth-child(1) {
    background-color: var(--color-destroy-700);
    animation-delay: 0.1s;
  }
  
  .building-block:nth-child(2) {
    background-color: var(--color-destroy-600);
    animation-delay: 0.2s;
  }
  
  .building-block:nth-child(3) {
    background-color: var(--color-destroy-500);
    animation-delay: 0.3s;
  }
  
  .debris {
    position: absolute;
    width: 4px;
    height: 4px;
    background-color: var(--color-destroy-700);
    animation: debris-fall 2s infinite ease-out;
  }
  
  .debris1 {
    left: 10px;
    animation-delay: 0.5s;
  }
  
  .debris2 {
    left: 30px;
    animation-delay: 1s;
    width: 3px;
    height: 3px;
  }
  
  .debris3 {
    left: 50px;
    animation-delay: 1.5s;
    width: 5px;
    height: 5px;
  }
  
  .debris4 {
    left: 20px;
    animation-delay: 2s;
    width: 2px;
    height: 2px;
  }
</style>