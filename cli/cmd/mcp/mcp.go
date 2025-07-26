package mcp

import (
	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
)

var globalConfig *config.Config

func NewMCPCommand() *cobra.Command {
	mcpCmd := &cobra.Command{
		Use:   "mcp",
		Short: "Manage Model Context Protocol server",
	}

	mcpCmd.AddCommand(newStartCommand())
	mcpCmd.AddCommand(newToolsCommand())
	mcpCmd.AddCommand(newStatusCommand())

	return mcpCmd
}

func SetGlobalConfig(cfg *config.Config) {
	globalConfig = cfg
}