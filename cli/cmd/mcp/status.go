package mcp

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
)

func newStatusCommand() *cobra.Command {
	statusCmd := &cobra.Command{
		Use:   "status",
		Short: "Check MCP server status and connectivity",
		Long:  "Check MCP server prerequisites and API connectivity.",
		RunE:  runStatusCommand,
	}

	return statusCmd
}

func runStatusCommand(cmd *cobra.Command, args []string) error {
	fmt.Println("OpenLabs MCP Server Status Check")

	if globalConfig == nil {
		logger.Failure("No configuration loaded")
		return fmt.Errorf("configuration not loaded")
	}
	logger.Success("Configuration loaded")

	logger.Success("API URL: %s", globalConfig.APIURL)

	if globalConfig.AuthToken == "" {
		logger.Failure("No auth token found")
		logger.Notice("Run 'openlabs auth login' to authenticate, or use the 'login' MCP tool")
		return nil
	}
	logger.Success("Authentication token present")

	apiClient := client.New(globalConfig)
	if err := apiClient.Ping(); err != nil {
		logger.Failure("API connectivity failed (%v)", err)
		logger.Debug("API ping failed: %v", err)

		logger.Notice("Troubleshooting steps:")
		fmt.Println("    1. Check your network connection")
		fmt.Println("    2. Verify API URL with 'openlabs config show'")
		fmt.Println("    3. Re-authenticate with 'openlabs auth login'")
		return nil
	}
	logger.Success("API connectivity verified")

	userInfo, err := apiClient.GetUserInfo()
	if err != nil {
		logger.Failure("Failed to get user info (%v)", err)
		logger.Notice("Your token may be expired. Run 'openlabs auth login' to re-authenticate, or use the 'login' MCP tool")
		return nil
	}
	logger.Success("User info: %s (%s)", userInfo.Name, userInfo.Email)

	logger.Success("MCP server is ready to start!")

	fmt.Println("\nQuick start commands:")
	fmt.Println("  openlabs mcp start              # Start with stdio transport")
	fmt.Println("  openlabs mcp start --debug      # Start with debug logging")
	fmt.Println("  openlabs mcp tools              # List available tools")

	return nil
}
