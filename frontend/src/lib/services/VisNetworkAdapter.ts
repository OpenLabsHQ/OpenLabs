/**
 * Adapter for vis-network library configuration and initialization
 */

export interface NetworkOptions {
  physics?: {
    enabled: boolean;
    solver: string;
    hierarchicalRepulsion?: {
      centralGravity: number;
      springLength: number;
      nodeDistance: number;
    };
    stabilization?: {
      enabled: boolean;
      iterations: number;
      updateInterval: number;
    };
  };
  nodes?: {
    size: number;
    font: { size: number };
  };
  edges?: {
    width: number;
    color: { color: string };
    smooth: { type: string };
  };
}

export class VisNetworkAdapter {
  private network: any = null;

  /**
   * Get default network visualization options
   */
  static getDefaultOptions(): NetworkOptions {
    return {
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
    };
  }

  /**
   * Create and initialize a vis-network instance
   */
  createNetwork(
    container: HTMLElement,
    data: { nodes: any; edges: any },
    Network: any,
    options?: NetworkOptions
  ): any {
    const networkOptions = options || VisNetworkAdapter.getDefaultOptions();
    
    this.network = new Network(container, data, networkOptions);
    
    this.setupNetworkEvents();
    
    return this.network;
  }

  /**
   * Setup network event handlers
   */
  private setupNetworkEvents(): void {
    if (!this.network) return;

    // Auto-fit the network once stabilization is complete
    this.network.once('stabilizationIterationsDone', () => {
      this.network.fit();
    });
  }

  /**
   * Get the current network instance
   */
  getNetwork(): any {
    return this.network;
  }

  /**
   * Destroy the network instance
   */
  destroy(): void {
    if (this.network) {
      this.network.destroy();
      this.network = null;
    }
  }

  /**
   * Fit the network view to show all nodes
   */
  fit(): void {
    if (this.network) {
      this.network.fit();
    }
  }

  /**
   * Redraw the network
   */
  redraw(): void {
    if (this.network) {
      this.network.redraw();
    }
  }

  /**
   * Check if the network is stabilized
   */
  isStabilized(): boolean {
    return this.network ? this.network.physics.stabilized : false;
  }
}