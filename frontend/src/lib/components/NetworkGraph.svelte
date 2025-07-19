<script>
  import { onMount } from 'svelte'
  import { browser } from '$app/environment'
  import LoadingSpinner from './LoadingSpinner.svelte'

  // Props
  export let blueprintData

  // Network visualization
  let network = null
  let container
  let error = ''

  // Loading state
  let isLoading = true

  // Initialize the network when the component mounts
  onMount(async () => {
    if (browser) {
      try {
        if (!blueprintData) {
          error = 'No blueprint data available'
          isLoading = false
          return
        }

        // Import vis-network dynamically (client-side only)
        const visJs = await import('vis-network/standalone')
        const { Network, DataSet } = visJs

        // Wait for DOM to be ready
        setTimeout(() => {
          if (!container) {
            error = 'Network visualization container not available'
            isLoading = false
            return
          }

          try {
            buildNetworkVisualization(Network, DataSet)
          } catch {
            error = 'Error building network visualization'
            isLoading = false
          }
        }, 200)
      } catch {
        error = 'Failed to initialize network visualization'
        isLoading = false
      }
    }
  })

  function buildNetworkVisualization(Network, DataSet) {
    // Create data structures
    const nodes = new DataSet()
    const edges = new DataSet()

    // Add Internet node
    nodes.add({
      id: 'internet',
      label: '<b>Internet</b>',
      shape: 'image',
      image: '/images/gw.svg',
      font: { multi: true },
      size: 40,
    })

    // Get VPC data - handle both single VPC and multiple VPCs
    let vpcs = []

    if (blueprintData.vpc) {
      // Single VPC structure
      vpcs = [blueprintData.vpc]
    } else if (
      blueprintData.vpcs &&
      Array.isArray(blueprintData.vpcs) &&
      blueprintData.vpcs.length > 0
    ) {
      // Array of VPCs
      vpcs = blueprintData.vpcs
    }

    if (!vpcs.length) {
      // Create a simple visualization with just Internet
      return { nodes, edges }
    }

    // Track all subnet IDs for jumpbox connections
    const allUserSubnetIds = []

    // Process each VPC
    vpcs.forEach((vpc, vpcIndex) => {
      if (!vpc) return

      // Create unique VPC ID using actual VPC ID if available, otherwise use index
      const vpcId = `vpc_${vpc.id || vpcIndex}`
      const vpcName = vpc.name || `VPC ${vpcIndex + 1}`
      const vpcCidr = vpc.cidr || ''

      // Add VPC node
      nodes.add({
        id: vpcId,
        label: `<b>${vpcName}</b>\n${vpcCidr}`,
        shape: 'image',
        image: '/images/vpc.svg',
        font: { multi: true },
        size: 40,
      })

      // Connect Internet to VPC
      edges.add({
        id: `edge_internet_${vpcId}`,
        from: 'internet',
        to: vpcId,
        dashes: true,
      })

      // Find subnets in different possible locations based on the API response structure
      let rawSubnets = null

      // Option 1: Direct subnets array in vpc
      if (Array.isArray(vpc.subnets)) {
        rawSubnets = vpc.subnets
      }
      // Option 2: Subnets might be in a 'subnet' property
      else if (vpc.subnet && Array.isArray(vpc.subnet)) {
        rawSubnets = vpc.subnet
      }
      // Option 3: If subnets is an object, convert to array
      else if (vpc.subnets && typeof vpc.subnets === 'object') {
        rawSubnets = Object.values(vpc.subnets)
      }

      // Create special Admin subnet with Jumpbox (implicit for every VPC)
      // CIDR is based on VPC CIDR with 3rd octet changed to 99
      let adminSubnetCidr = ''
      if (vpcCidr) {
        const vpcParts = vpcCidr.split('.')
        if (vpcParts.length >= 4) {
          // Replace the 3rd octet with 99
          vpcParts[2] = '99'
          // Use first 3 octets and make it a /24
          adminSubnetCidr = `${vpcParts[0]}.${vpcParts[1]}.${vpcParts[2]}.0/24`
        }
      }

      // If we couldn't derive the admin subnet CIDR, use a default based on VPC index
      if (!adminSubnetCidr) {
        adminSubnetCidr = `10.${vpcIndex}.99.0/24`
      }

      // Add Admin subnet node with unique ID
      const adminSubnetId = `admin_subnet_${vpc.id || vpcIndex}`
      nodes.add({
        id: adminSubnetId,
        label: `<b>Admin</b>\n${adminSubnetCidr}`,
        shape: 'image',
        image: '/images/subnet.svg',
        font: { multi: true },
        size: 40,
      })

      // Connect VPC to Admin subnet
      edges.add({
        id: `edge_${vpcId}_admin`,
        from: vpcId,
        to: adminSubnetId,
        dashes: true,
      })

      // Add Jumpbox host in Admin subnet with unique ID
      const jumpboxId = `jumpbox_${vpc.id || vpcIndex}`
      nodes.add({
        id: jumpboxId,
        label: `<b>JumpBox ${vpcName}</b>`,
        shape: 'image',
        image: '/images/system.svg',
        font: { multi: true },
        size: 30,
      })

      // Connect Admin subnet to Jumpbox
      edges.add({
        id: `edge_${adminSubnetId}_jumpbox`,
        from: adminSubnetId,
        to: jumpboxId,
        dashes: true,
      })

      // If there are no user-defined subnets, continue to next VPC
      if (!rawSubnets || !rawSubnets.length) {
        return
      }

      // Track subnet IDs for this VPC to connect Jumpbox to all subnets
      const vpcSubnetIds = []

      // Process each user-defined subnet in this VPC
      rawSubnets.forEach((subnet, subnetIndex) => {
        if (!subnet) {
          return
        }

        // Create unique subnet ID using VPC ID and subnet ID if available
        const subnetId = `subnet_${vpc.id || vpcIndex}_${subnet.id || subnetIndex}`
        const subnetName = subnet.name || `Subnet ${subnetIndex + 1}`
        const subnetCidr = subnet.cidr || ''

        // Add subnet node
        nodes.add({
          id: subnetId,
          label: `<b>${subnetName}</b>\n${subnetCidr}`,
          shape: 'image',
          image: '/images/subnet.svg',
          font: { multi: true },
          size: 40,
        })

        // Store subnet ID to connect Jumpbox later
        vpcSubnetIds.push(subnetId)
        allUserSubnetIds.push(subnetId)

        // Connect VPC to subnet
        edges.add({
          id: `edge_${vpcId}_${subnetId}`,
          from: vpcId,
          to: subnetId,
          dashes: true,
        })

        // Find hosts in different possible locations
        let rawHosts = null

        // Option 1: Direct hosts array in subnet
        if (Array.isArray(subnet.hosts)) {
          rawHosts = subnet.hosts
        }
        // Option 2: Hosts might be in a 'host' property
        else if (subnet.host && Array.isArray(subnet.host)) {
          rawHosts = subnet.host
        }
        // Option 3: If hosts is an object, convert to array
        else if (subnet.hosts && typeof subnet.hosts === 'object') {
          rawHosts = Object.values(subnet.hosts)
        }

        if (!rawHosts || !rawHosts.length) {
          return
        }

        // Process each host
        rawHosts.forEach((host, hostIndex) => {
          if (!host) {
            return
          }

          // Create unique host ID using VPC, subnet, and host IDs
          const hostId = `host_${vpc.id || vpcIndex}_${subnet.id || subnetIndex}_${host.id || hostIndex}`
          // Check for either hostname or name property
          const hostName = host.hostname || host.name || `Host ${hostIndex + 1}`
          // Host OS and spec information is available but not displayed in the visualization

          // Show hostname and IP (if available) in the network visualization
          let hostLabel = `<b>${hostName}</b>`

          // Add IP address if available
          if (host.ip) {
            hostLabel += `\n${host.ip}`
          }

          // Add host node
          nodes.add({
            id: hostId,
            label: hostLabel,
            shape: 'image',
            image: '/images/system.svg',
            font: { multi: true },
            size: 30,
          })

          // Connect subnet to host
          edges.add({
            id: `edge_${subnetId}_${hostId}`,
            from: subnetId,
            to: hostId,
            dashes: true,
          })
        })
      })

      // Connect Jumpbox to all user-defined subnets in this VPC
      vpcSubnetIds.forEach((subnetId) => {
        edges.add({
          id: `edge_${jumpboxId}_${subnetId}`,
          from: jumpboxId,
          to: subnetId,
          dashes: true,
        })
      })
    })

    // Add VPN-ed Attackers node only if VPN is enabled
    const vpnEnabled = blueprintData.vpn === true

    if (vpnEnabled && vpcs.length > 0) {
      // Add VPN-ed Attackers node (connected to the first VPC's jumpbox)
      const firstJumpboxId = `jumpbox_${vpcs[0].id || 0}`
      
      nodes.add({
        id: 'vpn_attackers',
        label: '<b>VPN-ed Attackers</b>',
        shape: 'image',
        image: '/images/vpn.svg',
        font: { multi: true },
        size: 30,
      })

      // Connect VPN-ed Attackers to first jumpbox
      edges.add({
        id: 'edge_vpn_jumpbox',
        from: 'vpn_attackers',
        to: firstJumpboxId,
        dashes: true,
      })
    }

    // Network visualization options
    const options = {
      physics: {
        enabled: true,
        solver: 'hierarchicalRepulsion',
        hierarchicalRepulsion: {
          centralGravity: 0.0,
          springLength: 120,
          nodeDistance: 120,
        },
        stabilization: {
          enabled: true,
          iterations: 200,
          updateInterval: 20,
        },
      },
      nodes: {
        size: 30,
        font: { size: 16 },
      },
      edges: {
        width: 2,
        color: { color: 'gray' },
        smooth: { type: 'continuous' },
      },
    }

    // Create the network
    network = new Network(container, { nodes, edges }, options)

    // Initialize the network
    network.once('stabilizationIterationsDone', function () {
      network.fit()
    })

    // Set loading to false once the network is initialized
    isLoading = false

    return { nodes, edges }
  }
</script>

{#if error}
  <div
    class="rounded border-l-4 border-red-500 bg-red-50 p-4 text-red-700 shadow-md"
  >
    <p class="mb-2 font-bold">Network Visualization Error</p>
    <p>{error}</p>
  </div>
{:else}
  <div
    bind:this={container}
    class="relative h-[500px] rounded border border-gray-200"
  >
    {#if isLoading}
      <LoadingSpinner
        size="medium"
        color="blue"
        message="Loading network diagram..."
        overlay={true}
      />
    {/if}
  </div>
{/if}

<style>
  /* Ensure the network visualization looks good */
  :global(.vis-network) {
    outline: none;
  }
</style>
