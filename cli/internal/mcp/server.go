package mcp

import (
	"context"
	"fmt"
	"log"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
)

type Server struct {
	mcpServer *server.MCPServer
	client    *client.Client
	config    *config.Config
	debug     bool
}

func NewServer(cfg *config.Config, debug bool) (*Server, error) {
	if cfg == nil {
		return nil, fmt.Errorf("configuration is required")
	}

	apiClient := client.New(cfg)

	s := &Server{
		client: apiClient,
		config: cfg,
		debug:  debug,
	}

	mcpServer := server.NewMCPServer(
		"OpenLabs MCP Server",
		"1.0.0",
		server.WithToolCapabilities(false),
		server.WithRecovery(),
		server.WithInstructions(s.getOpenLabsInstructions()),
	)

	s.mcpServer = mcpServer

	if err := s.registerTools(); err != nil {
		return nil, fmt.Errorf("failed to register tools: %w", err)
	}

	return s, nil
}

func (s *Server) reloadConfigIfChanged() bool {
	newConfig, err := config.Load()
	if err != nil {
		if s.debug {
			logger.Debug("Failed to reload config: %v", err)
		}
		return false
	}
	
	if newConfig.AuthToken != s.config.AuthToken {
		if s.debug {
			logger.Debug("Auth token changed, updating client configuration")
		}
		
		s.config = newConfig
		s.client = client.New(newConfig)
		
		return true
	}
	
	return false
}

func (s *Server) RunStdio(ctx context.Context) error {
	if s.debug {
		log.Println("Starting MCP server with stdio transport")
	}

	errChan := make(chan error, 1)
	go func() {
		errChan <- server.ServeStdio(s.mcpServer)
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		return ctx.Err()
	}
}

func (s *Server) RunSSE(ctx context.Context, addr string) error {
	if s.debug {
		log.Printf("Starting MCP server with SSE transport on %s", addr)
	}

	port := ":8080"
	if addr != "" {
		port = addr
	}

	sseServer := server.NewSSEServer(
		s.mcpServer,
		server.WithSSEEndpoint("/sse"),
		server.WithMessageEndpoint("/message"),
		server.WithBaseURL(fmt.Sprintf("http://localhost%s", port)),
		server.WithUseFullURLForMessageEndpoint(true),
	)
	
	log.Printf("SSE server listening on %s with endpoints /sse and /message", port)
	
	errChan := make(chan error, 1)
	go func() {
		errChan <- sseServer.Start(port)
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		if err := sseServer.Shutdown(context.Background()); err != nil {
			log.Printf("Error during SSE server shutdown: %v", err)
		}
		return ctx.Err()
	}
}

func (s *Server) registerTools() error {
	tools := GetAllTools()
	
	for _, tool := range tools {
		handler := s.createToolHandler(tool.Name)
		s.mcpServer.AddTool(tool, handler)
	}
	
	return nil
}

func (s *Server) getOpenLabsInstructions() string {
	isAuthenticated := s.client.IsAuthenticated()
	var userContext string
	var isAdmin bool
	
	if isAuthenticated {
		userInfo, err := s.client.GetUserInfo()
		if err != nil {
			userContext = "[!] Authentication token present but failed to get user info - token may be expired"
		} else {
			isAdmin = userInfo.Admin
					 
			adminStatus := "Standard User"
			if isAdmin {
				adminStatus = "Administrator"
			}
			
			userContext = fmt.Sprintf("[+] Authenticated as: %s (%s) - Role: %s", 
				userInfo.Name, userInfo.Email, adminStatus)
		}
	} else {
		userContext = "[-] Not authenticated - user must login to access OpenLabs resources"
	}

	return fmt.Sprintf(`# OpenLabs MCP Server Instructions

You are working with the OpenLabs MCP server, which provides access to a cloud-based cybersecurity training and lab deployment platform.

## Current User Status
%s

## What is OpenLabs?
OpenLabs allows users to:
- Deploy virtual security training ranges in the cloud (AWS, Azure)
- Access pre-built cybersecurity lab blueprints and scenarios
- Create custom training environments and share them
- Manage cloud credentials and deployments
- Track deployment status and costs

## CRITICAL Authentication Requirements
[!] **IMPORTANT**: Nearly all OpenLabs operations require authentication.
- Users must be logged in to list, deploy, or manage ranges
- Users must be logged in to access blueprints and create new ones
- Users must be logged in to manage cloud credentials
- Only the 'login' tool and basic status checks work without authentication

## Authentication Best Practices
1. **PREFERRED METHOD**: Always guide users to use CLI authentication first:
   - Ask user to run 'openlabs auth login' in their terminal
   - This is the most secure method as credentials don't travel over MCP
   - Then retry the requested operation

2. **Alternative method** (use only if CLI method fails):
   - WARN the user: "For security, 'openlabs auth login' is preferred. MCP login sends credentials over the protocol."
   - Only proceed if user explicitly confirms they want to use MCP login
   - Call the 'login' tool with email and password parameters

## User Capabilities
%s

## Available Operations
**Range Management:**
- List deployed ranges and get details
- Deploy new ranges from blueprints  
- Destroy ranges (irreversible - requires confirmation)
- Get SSH keys for accessing deployed ranges

**Blueprint Management:**
- List available blueprints
- Get blueprint details and specifications
- Create new blueprints from JSON (admin/advanced users)
- Delete blueprints (irreversible - requires confirmation)

**Cloud Integration:**
- Update AWS credentials (access key, secret key)
- Update Azure credentials (client ID, secret, tenant, subscription)
- Deploy ranges to specific cloud regions

**Job Monitoring:**
- Check status of deployment/destruction jobs
- Monitor long-running operations

## Best Practices for LLM Behavior
1. **Always check authentication first** - Use 'get_user_info' or check for auth errors
2. **Guide users to CLI login** - 'openlabs auth login' is the preferred method
3. **Confirm destructive operations** - Ranges and blueprints cannot be recovered once deleted
4. **Provide clear feedback** - Users need to know the status of long-running deployments
5. **Be security conscious** - Warn about credential handling and destructive operations
6. **Handle auth errors properly** - When you get auth errors, guide users to login via CLI first`, 
		userContext, s.getUserCapabilitiesText(isAuthenticated, isAdmin))
}

func (s *Server) getUserCapabilitiesText(isAuthenticated, isAdmin bool) string {
	if !isAuthenticated {
		return `[-] **Not Authenticated**: No access to OpenLabs resources
- Cannot list or manage ranges
- Cannot access blueprints  
- Cannot manage cloud credentials
- Must authenticate first using 'openlabs auth login' or the MCP login tool`
	}
	
	if isAdmin {
		return `[+] **Administrator Access**: Full platform capabilities
- Can create and delete blueprints
- Can deploy and destroy ranges
- Can manage all cloud credentials
- Has access to all platform features
- Can perform administrative operations`
	}
	
	return `[+] **Standard User Access**: Core platform capabilities
- Can list and deploy ranges from existing blueprints
- Can destroy own deployed ranges
- Can manage own cloud credentials
- Can access most platform features
- May have limited blueprint creation capabilities`
}

func (s *Server) createToolHandler(toolName string) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		logger.Debug("MCP tool invoked: %s", toolName)
		
		switch toolName {
		case "list_ranges":
			return s.handleListRanges(ctx, request)
		case "get_range_details":
			return s.handleGetRangeDetails(ctx, request)
		case "get_range_key":
			return s.handleGetRangeKey(ctx, request)
		case "list_blueprints":
			return s.handleListBlueprints(ctx, request)
		case "get_blueprint_details":
			return s.handleGetBlueprintDetails(ctx, request)
		case "check_job_status":
			return s.handleCheckJobStatus(ctx, request)
		case "get_user_info":
			return s.handleGetUserInfo(ctx, request)
		case "deploy_range":
			return s.handleDeployRange(ctx, request)
		case "destroy_range":
			return s.handleDestroyRange(ctx, request)
		case "create_blueprint":
			return s.handleCreateBlueprint(ctx, request)
		case "delete_blueprint":
			return s.handleDeleteBlueprint(ctx, request)
		case "update_aws_secrets":
			return s.handleUpdateAWSSecrets(ctx, request)
		case "update_azure_secrets":
			return s.handleUpdateAzureSecrets(ctx, request)
		case "login":
			return s.handleLogin(ctx, request)
		default:
			return mcp.NewToolResultError(fmt.Sprintf("Unknown tool: %s", toolName)), nil
		}
	}
}