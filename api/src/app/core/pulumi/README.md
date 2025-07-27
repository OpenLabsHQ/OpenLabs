# Pulumi Integration for OpenLabs

This directory contains the Pulumi-based infrastructure deployment system that replaces the previous CDKTF implementation.

## Architecture

### Base Classes

- **`AbstractBasePulumiRange`** (`base_range.py`): Abstract base class that defines the common interface for all cloud providers
- **`AWSPulumiRange`** (`aws_range.py`): AWS-specific implementation using Pulumi AWS provider
- **`PulumiRangeFactory`** (`range_factory.py`): Factory class to create provider-specific range instances

### Key Differences from CDKTF

1. **No Synthesis Step**: Pulumi doesn't require a separate synthesis step like CDKTF
2. **State Management**: Uses Pulumi's native state management instead of Terraform state files
3. **Programming Model**: Pure Python functions instead of class-based constructs
4. **Automation API**: Uses Pulumi's Automation API for programmatic deployment

### State Management

- **CDKTF**: Used `terraform.tfstate` files stored in temporary directories
- **Pulumi**: Uses Pulumi's state management system with backends (can be local files, S3, Pulumi Cloud, etc.)
- **Compatibility**: The `state_file` field in the database now stores Pulumi state data instead of Terraform state

### Deployment Flow

1. **Create Stack**: Create a Pulumi stack with appropriate configuration
2. **Install Plugins**: Install required cloud provider plugins
3. **Deploy**: Run `pulumi up` via Automation API
4. **Parse Outputs**: Extract infrastructure details from Pulumi outputs
5. **Store State**: Save Pulumi state data to database

### Destruction Flow

1. **Recreate Stack**: Recreate the Pulumi stack from stored state
2. **Import State**: Import the previous state into the stack
3. **Destroy**: Run `pulumi destroy` via Automation API
4. **Cleanup**: Remove temporary workspace files

## Configuration

The system reuses the existing `CDKTF_DIR` configuration setting (now pointing to Pulumi workspace directories) to maintain compatibility with existing code.

## Dependencies

- `pulumi>=3.0.0`: Core Pulumi Python SDK
- `pulumi-aws>=6.0.0`: AWS provider for Pulumi

## Migration from CDKTF

The migration maintains API compatibility:
- Same database schema (state stored in `state_file` field)
- Same function signatures for deployment/destruction
- Same output parsing logic
- Same credential management

## Future Enhancements

1. **Multiple Backends**: Configure different Pulumi backends for different environments
2. **Stack Policies**: Implement Pulumi stack policies for governance
3. **Component Resources**: Create reusable Pulumi component resources
4. **Multi-Cloud**: Easy extension to other cloud providers using Pulumi's unified API