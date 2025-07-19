// Eventually we need to grab this (probably on start) from the API.

export type OpenLabsSpec = 'tiny' | 'small' | 'medium' | 'large' | 'huge'

export const SpecOptions = [
  { value: 'tiny', label: 'Tiny (1 vCPU, 0.5 GiB RAM)' },
  { value: 'small', label: 'Small (1 vCPU, 2.0 GiB RAM)' },
  { value: 'medium', label: 'Medium (2 vCPU, 4.0 GiB RAM)' },
  { value: 'large', label: 'Large (2 vCPU, 8.0 GiB RAM)' },
  { value: 'huge', label: 'Huge (4 vCPU, 16.0 GiB RAM)' },
]
