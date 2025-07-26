package prompts

const AdminCapabilities = `[+] **Administrator Access**: Full platform capabilities
- Can create and delete blueprints
- Can deploy and destroy ranges
- Can manage all cloud credentials
- Has access to all platform features
- Can perform administrative operations`

const StandardCapabilities = `[+] **Standard User Access**: Core platform capabilities
- Can list and deploy ranges from existing blueprints
- Can destroy own deployed ranges
- Can manage own cloud credentials
- Can access most platform features
- May have limited blueprint creation capabilities`

const UnauthenticatedCapabilities = `[-] **Not Authenticated**: No access to OpenLabs resources
- Cannot list or manage ranges
- Cannot access blueprints  
- Cannot manage cloud credentials
- Must authenticate first using 'openlabs auth login' or the MCP login tool`