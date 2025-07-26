package mcp

import (
	"context"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/mcp/prompts"
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
		logger.Debug("Starting MCP server with stdio transport")
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
		logger.Debug("Starting MCP server with SSE transport on %s", addr)
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
	
	logger.Info("SSE server listening on %s with endpoints /sse and /message", port)
	
	errChan := make(chan error, 1)
	go func() {
		errChan <- sseServer.Start(port)
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		if err := sseServer.Shutdown(context.Background()); err != nil {
			logger.Error("Error during SSE server shutdown: %v", err)
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

	return fmt.Sprintf(prompts.MainInstructionsTemplate, 
		userContext, s.getUserCapabilitiesText(isAuthenticated, isAdmin))
}

func (s *Server) getUserCapabilitiesText(isAuthenticated, isAdmin bool) string {
	if !isAuthenticated {
		return prompts.UnauthenticatedCapabilities
	}
	
	if isAdmin {
		return prompts.AdminCapabilities
	}
	
	return prompts.StandardCapabilities
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