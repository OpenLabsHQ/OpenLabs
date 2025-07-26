package mcp

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/mcp"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
)

func newToolsCommand() *cobra.Command {
	toolsCmd := &cobra.Command{
		Use:   "tools",
		Short: "List available MCP tools",
		Long:  "List all Model Context Protocol tools available to AI assistants.",
		RunE:  runToolsCommand,
	}

	return toolsCmd
}

func runToolsCommand(cmd *cobra.Command, args []string) error {
	tools := mcp.GetAllTools()

	if globalConfig.OutputFormat == "table" || globalConfig.OutputFormat == "" {
		if err := output.DisplayMCPTools(tools); err != nil {
			return fmt.Errorf("failed to display tools: %w", err)
		}
	} else {
		if err := output.Display(tools, globalConfig.OutputFormat); err != nil {
			return fmt.Errorf("failed to display tools: %w", err)
		}
	}

	return nil
}