// Eventually we need to grab this (probably on start) from the API.
export type OpenLabsOS =
  | 'debian_11'
  | 'debian_12'
  | 'ubuntu_20'
  | 'ubuntu_22'
  | 'ubuntu_24'
  | 'suse_12'
  | 'suse_15'
  | 'kali'
  | 'windows_2016'
  | 'windows_2019'
  | 'windows_2022'

export const OSOptions = [
  { value: 'debian_11', label: 'Debian 11' },
  { value: 'debian_12', label: 'Debian 12' },
  { value: 'ubuntu_20', label: 'Ubuntu 20.04' },
  { value: 'ubuntu_22', label: 'Ubuntu 22.04' },
  { value: 'ubuntu_24', label: 'Ubuntu 24.04' },
  { value: 'suse_12', label: 'SUSE 12' },
  { value: 'suse_15', label: 'SUSE 15' },
  { value: 'kali', label: 'Kali Linux' },
  { value: 'windows_2016', label: 'Windows Server 2016' },
  { value: 'windows_2019', label: 'Windows Server 2019' },
  { value: 'windows_2022', label: 'Windows Server 2022' },
]

export const osSizeThresholds: Record<OpenLabsOS, number> = {
  debian_11: 8,
  debian_12: 8,
  ubuntu_20: 8,
  ubuntu_22: 8,
  ubuntu_24: 8,
  suse_12: 8,
  suse_15: 8,
  kali: 32,
  windows_2016: 32,
  windows_2019: 32,
  windows_2022: 32,
}
