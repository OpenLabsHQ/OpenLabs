# Example Templates

Templates can be made in YAML for human-readability or in JSON for verbosity

### Example 1: Basic Network

```yaml
Range:
  Name: ADPractice
  Config:
    VPN: yes
    VNC: no
    Provider: AWS

  Network:
    VPC:
      Name: CorpVPC
      CIDR: 10.0.0.0/16
      Subnets:
        - Name: Dev
          CIDR: 10.0.1.0/24
          Hosts:
            - Hostname: Web
              OS: Debian12
              Size: Huge
              Tags:
                - Web
                - Dev
                - Linux

            - Hostname: Linux01
              OS: Ubuntu22
              Size: Medium
              Tags:
                - Dev
                - Linux

            - Hostname: Linux02
              OS: CentOS8
              Size: Medium
              Tags:
                - Dev
                - Linux

        - Name: AD
          CIDR: 10.0.2.0/24
          Hosts:
            - Hostname: DC01
              OS: Windows2022
              Size: Large
              Tags:
                - DC
                - AD
                - Windows

            - Hostname: Workstation01
              OS: Windows10
              Size: Medium
              Tags:
                - Workstation
                - User
                - Windows
            
```
