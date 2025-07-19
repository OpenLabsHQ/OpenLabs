# OpenLabs CLI

A command-line interface for managing cyber ranges, blueprints, and cloud infrastructure with OpenLabs.

## Installation

### Pre-built Binaries

Download the latest release for your platform from [GitHub Releases](https://github.com/OpenLabsHQ/CLI/releases).

Available packages:
- **Linux**: `openlabs-linux-amd64`
- **macOS**: `openlabs-darwin-amd64` 
- **Windows**: `openlabs-windows-amd64.exe`

### Build from Source

```bash
# Using Makefile
make build

# Or build directly with Go
go build -o openlabs
```

## Quick Start

```bash
# Authenticate
openlabs auth login

# List available blueprints
openlabs blueprints list

# Deploy a range
openlabs range deploy my-blueprint --name "test-range"

# Check deployment status
openlabs range jobs

# View range details
openlabs range status

# Destroy a range
openlabs range destroy test-range
```

## Commands

### Authentication
- `openlabs auth login` - Log in to OpenLabs
- `openlabs auth logout` - Log out
- `openlabs auth status` - Check authentication status

### Blueprints
- `openlabs blueprints list` - List available blueprints
- `openlabs blueprints show <id>` - Show blueprint details
- `openlabs blueprints create` - Create new blueprint
- `openlabs blueprints delete <id>` - Delete blueprint

### Ranges
- `openlabs range list` - List deployed ranges
- `openlabs range deploy <blueprint>` - Deploy a range
- `openlabs range destroy <range>` - Destroy a range
- `openlabs range status [range]` - Show range status
- `openlabs range jobs` - List deployment jobs
- `openlabs range key [range]` - Get SSH private key

### Configuration
- `openlabs config show` - Show current configuration
- `openlabs config set <key> <value>` - Set configuration value

## Global Flags

- `--format` - Output format (table, json, yaml)
- `--config` - Configuration file path
- `--api-url` - OpenLabs API URL
- `--verbose` - Enable verbose output

## Configuration

The CLI stores configuration in `~/.openlabs/config.json`:

```json
{
  "api_url": "https://api.openlabs.sh",
  "output_format": "table",
  "timeout": "10m"
}
```
