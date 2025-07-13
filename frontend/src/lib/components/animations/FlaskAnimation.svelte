<script lang="ts">
  export let label: string = 'Creating resources'
  export let color: 'blue' | 'red' = 'blue'
  
  const colorClasses = {
    blue: {
      text: 'text-blue-700',
      flask: '#6495ED',
      liquid: 'rgba(65, 105, 225, 0.7)',
      background: 'rgba(161, 216, 230, 0.2)'
    },
    red: {
      text: 'text-red-700', 
      flask: '#dc2626',
      liquid: 'rgba(239, 68, 68, 0.7)',
      background: 'rgba(254, 202, 202, 0.2)'
    }
  }
  
  $: colors = colorClasses[color]
</script>

<div class="flex flex-col items-center">
  <div class="flask" style="--flask-color: {colors.flask}; --liquid-color: {colors.liquid}; --bg-color: {colors.background}">
    <div class="flask-liquid">
      <div class="bubble"></div>
      <div class="bubble"></div>
      <div class="bubble"></div>
      <div class="bubble"></div>
      <div class="bubble"></div>
      <div class="bubble"></div>
      <div class="bubble"></div>
    </div>
  </div>
  <p class="mt-2 text-sm font-medium {colors.text}">{label}</p>
</div>

<style>
  /* Flask and bubble animation */
  @keyframes bubble {
    0% {
      bottom: 0;
      opacity: 0;
    }
    10% {
      opacity: 0.8;
    }
    80% {
      opacity: 0.8;
    }
    100% {
      bottom: 100%;
      opacity: 0;
    }
  }
  
  .bubble {
    position: absolute;
    width: 8px;
    height: 8px;
    background-color: rgba(255, 255, 255, 0.9);
    border-radius: 50%;
    animation: bubble 3s infinite ease-out;
    bottom: 0;
    box-shadow: 0 0 2px rgba(255, 255, 255, 0.5);
  }
  
  .bubble:nth-child(1) {
    left: 30%;
    animation-delay: 0.2s;
    width: 10px;
    height: 10px;
  }
  
  .bubble:nth-child(2) {
    left: 45%;
    animation-delay: 1.3s;
  }
  
  .bubble:nth-child(3) {
    left: 60%;
    width: 6px;
    height: 6px;
    animation-delay: 0.7s;
    animation-duration: 2.5s;
  }
  
  .bubble:nth-child(4) {
    left: 37%;
    width: 5px;
    height: 5px;
    animation-delay: 2.2s;
    animation-duration: 3.5s;
  }
  
  .bubble:nth-child(5) {
    left: 53%;
    width: 7px;
    height: 7px;
    animation-delay: 0.5s;
    animation-duration: 4s;
  }
  
  .bubble:nth-child(6) {
    left: 68%;
    width: 6px;
    height: 6px;
    animation-delay: 1.8s;
  }
  
  .bubble:nth-child(7) {
    left: 40%;
    width: 4px;
    height: 4px;
    animation-delay: 3s;
    animation-duration: 2.8s;
  }
  
  .flask {
    position: relative;
    width: 80px;
    height: 100px;
    background-color: var(--bg-color);
    border-radius: 0 0 40px 40px;
    border: 4px solid var(--flask-color);
    border-top: none;
    margin: 0 auto;
    overflow: hidden;
  }
  
  .flask::before {
    content: '';
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 20px;
    background-color: var(--flask-color);
    border-radius: 10px 10px 0 0;
  }
  
  .flask-liquid {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 60%;
    background-color: var(--liquid-color);
    border-radius: 0 0 36px 36px;
    overflow: hidden;
  }
</style>