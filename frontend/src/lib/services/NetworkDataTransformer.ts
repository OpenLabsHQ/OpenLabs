/**
 * Service for transforming blueprint data into network visualization data
 */

// DataSet type is passed in constructor, no direct import needed

export interface NetworkData {
  nodes: any;
  edges: any;
}

export interface VpcData {
  id?: string | number;
  name?: string;
  cidr?: string;
  subnets?: any[];
  subnet?: any[];
}

export interface SubnetData {
  id?: string | number;
  name?: string;
  cidr?: string;
  hosts?: any[];
  host?: any[];
}

export interface HostData {
  id?: string | number;
  hostname?: string;
  name?: string;
  ip?: string;
}

export class NetworkDataTransformer {
  private nodes: any;
  private edges: any;

  constructor(DataSet: any) {
    this.nodes = new DataSet();
    this.edges = new DataSet();
  }

  /**
   * Transform blueprint data into network visualization data
   */
  transform(blueprintData: any): NetworkData {
    this.addInternetNode();
    
    const vpcs = this.extractVpcs(blueprintData);
    if (!vpcs.length) {
      return { nodes: this.nodes, edges: this.edges };
    }

    vpcs.forEach((vpc, index) => this.processVpc(vpc, index));
    
    this.addVpnNode(blueprintData, vpcs);
    
    return { nodes: this.nodes, edges: this.edges };
  }

  /**
   * Add the Internet node to the network
   */
  private addInternetNode(): void {
    this.nodes.add({
      id: 'internet',
      label: '<b>Internet</b>',
      shape: 'image',
      image: '/images/gw.svg',
      font: { multi: true },
      size: 40,
    });
  }

  /**
   * Extract VPCs from blueprint data, handling different data structures
   */
  private extractVpcs(blueprintData: any): VpcData[] {
    if (blueprintData.vpc) {
      return [blueprintData.vpc];
    }
    
    if (blueprintData.vpcs && Array.isArray(blueprintData.vpcs) && blueprintData.vpcs.length > 0) {
      return blueprintData.vpcs;
    }
    
    return [];
  }

  /**
   * Process a single VPC and all its components
   */
  private processVpc(vpc: VpcData, vpcIndex: number): void {
    if (!vpc) return;

    const vpcId = `vpc_${vpc.id || vpcIndex}`;
    const vpcName = vpc.name || `VPC ${vpcIndex + 1}`;
    const vpcCidr = vpc.cidr || '';

    this.addVpcNode(vpcId, vpcName, vpcCidr);
    this.connectInternetToVpc(vpcId);
    
    const adminSubnetId = this.addAdminSubnet(vpc, vpcIndex, vpcId, vpcName, vpcCidr);
    const jumpboxId = this.addJumpbox(vpc, vpcIndex, vpcName, adminSubnetId);
    
    const subnets = this.extractSubnets(vpc);
    if (!subnets.length) return;

    const vpcSubnetIds = this.processSubnets(subnets, vpc, vpcIndex, vpcId);
    this.connectJumpboxToSubnets(jumpboxId, vpcSubnetIds);
  }

  /**
   * Add a VPC node to the network
   */
  private addVpcNode(vpcId: string, vpcName: string, vpcCidr: string): void {
    this.nodes.add({
      id: vpcId,
      label: `<b>${vpcName}</b>\n${vpcCidr}`,
      shape: 'image',
      image: '/images/vpc.svg',
      font: { multi: true },
      size: 40,
    });
  }

  /**
   * Connect Internet node to VPC
   */
  private connectInternetToVpc(vpcId: string): void {
    this.edges.add({
      id: `edge_internet_${vpcId}`,
      from: 'internet',
      to: vpcId,
      dashes: true,
    });
  }

  /**
   * Add admin subnet with calculated CIDR
   */
  private addAdminSubnet(vpc: VpcData, vpcIndex: number, vpcId: string, vpcName: string, vpcCidr: string): string {
    const adminSubnetCidr = this.calculateAdminSubnetCidr(vpcCidr, vpcIndex);
    const adminSubnetId = `admin_subnet_${vpc.id || vpcIndex}`;

    this.nodes.add({
      id: adminSubnetId,
      label: `<b>Admin</b>\n${adminSubnetCidr}`,
      shape: 'image',
      image: '/images/subnet.svg',
      font: { multi: true },
      size: 40,
    });

    this.edges.add({
      id: `edge_${vpcId}_admin`,
      from: vpcId,
      to: adminSubnetId,
      dashes: true,
    });

    return adminSubnetId;
  }

  /**
   * Calculate admin subnet CIDR based on VPC CIDR
   */
  private calculateAdminSubnetCidr(vpcCidr: string, vpcIndex: number): string {
    if (vpcCidr) {
      const vpcParts = vpcCidr.split('.');
      if (vpcParts.length >= 4) {
        vpcParts[2] = '99';
        return `${vpcParts[0]}.${vpcParts[1]}.${vpcParts[2]}.0/24`;
      }
    }
    return `10.${vpcIndex}.99.0/24`;
  }

  /**
   * Add jumpbox host to admin subnet
   */
  private addJumpbox(vpc: VpcData, vpcIndex: number, vpcName: string, adminSubnetId: string): string {
    const jumpboxId = `jumpbox_${vpc.id || vpcIndex}`;

    this.nodes.add({
      id: jumpboxId,
      label: `<b>JumpBox ${vpcName}</b>`,
      shape: 'image',
      image: '/images/system.svg',
      font: { multi: true },
      size: 30,
    });

    this.edges.add({
      id: `edge_${adminSubnetId}_jumpbox`,
      from: adminSubnetId,
      to: jumpboxId,
      dashes: true,
    });

    return jumpboxId;
  }

  /**
   * Extract subnets from VPC data, handling different data structures
   */
  private extractSubnets(vpc: VpcData): SubnetData[] {
    if (Array.isArray(vpc.subnets)) {
      return vpc.subnets;
    }
    if (vpc.subnet && Array.isArray(vpc.subnet)) {
      return vpc.subnet;
    }
    if (vpc.subnets && typeof vpc.subnets === 'object') {
      return Object.values(vpc.subnets);
    }
    return [];
  }

  /**
   * Process all subnets in a VPC
   */
  private processSubnets(subnets: SubnetData[], vpc: VpcData, vpcIndex: number, vpcId: string): string[] {
    const vpcSubnetIds: string[] = [];

    subnets.forEach((subnet, subnetIndex) => {
      if (!subnet) return;

      const subnetId = `subnet_${vpc.id || vpcIndex}_${subnet.id || subnetIndex}`;
      const subnetName = subnet.name || `Subnet ${subnetIndex + 1}`;
      const subnetCidr = subnet.cidr || '';

      this.addSubnetNode(subnetId, subnetName, subnetCidr);
      this.connectVpcToSubnet(vpcId, subnetId);
      vpcSubnetIds.push(subnetId);

      const hosts = this.extractHosts(subnet);
      this.processHosts(hosts, vpc, vpcIndex, subnet, subnetIndex, subnetId);
    });

    return vpcSubnetIds;
  }

  /**
   * Add a subnet node to the network
   */
  private addSubnetNode(subnetId: string, subnetName: string, subnetCidr: string): void {
    this.nodes.add({
      id: subnetId,
      label: `<b>${subnetName}</b>\n${subnetCidr}`,
      shape: 'image',
      image: '/images/subnet.svg',
      font: { multi: true },
      size: 40,
    });
  }

  /**
   * Connect VPC to subnet
   */
  private connectVpcToSubnet(vpcId: string, subnetId: string): void {
    this.edges.add({
      id: `edge_${vpcId}_${subnetId}`,
      from: vpcId,
      to: subnetId,
      dashes: true,
    });
  }

  /**
   * Extract hosts from subnet data, handling different data structures
   */
  private extractHosts(subnet: SubnetData): HostData[] {
    if (Array.isArray(subnet.hosts)) {
      return subnet.hosts;
    }
    if (subnet.host && Array.isArray(subnet.host)) {
      return subnet.host;
    }
    if (subnet.hosts && typeof subnet.hosts === 'object') {
      return Object.values(subnet.hosts);
    }
    return [];
  }

  /**
   * Process all hosts in a subnet
   */
  private processHosts(
    hosts: HostData[], 
    vpc: VpcData, 
    vpcIndex: number, 
    subnet: SubnetData, 
    subnetIndex: number, 
    subnetId: string
  ): void {
    if (!hosts.length) return;

    hosts.forEach((host, hostIndex) => {
      if (!host) return;

      const hostId = `host_${vpc.id || vpcIndex}_${subnet.id || subnetIndex}_${host.id || hostIndex}`;
      const hostName = host.hostname || host.name || `Host ${hostIndex + 1}`;
      
      let hostLabel = `<b>${hostName}</b>`;
      if (host.ip) {
        hostLabel += `\n${host.ip}`;
      }

      this.addHostNode(hostId, hostLabel);
      this.connectSubnetToHost(subnetId, hostId);
    });
  }

  /**
   * Add a host node to the network
   */
  private addHostNode(hostId: string, hostLabel: string): void {
    this.nodes.add({
      id: hostId,
      label: hostLabel,
      shape: 'image',
      image: '/images/system.svg',
      font: { multi: true },
      size: 30,
    });
  }

  /**
   * Connect subnet to host
   */
  private connectSubnetToHost(subnetId: string, hostId: string): void {
    this.edges.add({
      id: `edge_${subnetId}_${hostId}`,
      from: subnetId,
      to: hostId,
      dashes: true,
    });
  }

  /**
   * Connect jumpbox to all user-defined subnets
   */
  private connectJumpboxToSubnets(jumpboxId: string, subnetIds: string[]): void {
    subnetIds.forEach((subnetId) => {
      this.edges.add({
        id: `edge_${jumpboxId}_${subnetId}`,
        from: jumpboxId,
        to: subnetId,
        dashes: true,
      });
    });
  }

  /**
   * Add VPN node if VPN is enabled
   */
  private addVpnNode(blueprintData: any, vpcs: VpcData[]): void {
    const vpnEnabled = blueprintData.vpn === true;
    
    if (vpnEnabled && vpcs.length > 0) {
      const firstJumpboxId = `jumpbox_${vpcs[0].id || 0}`;
      
      this.nodes.add({
        id: 'vpn_attackers',
        label: '<b>VPN-ed Attackers</b>',
        shape: 'image',
        image: '/images/vpn.svg',
        font: { multi: true },
        size: 30,
      });

      this.edges.add({
        id: 'edge_vpn_jumpbox',
        from: 'vpn_attackers',
        to: firstJumpboxId,
        dashes: true,
      });
    }
  }
}
