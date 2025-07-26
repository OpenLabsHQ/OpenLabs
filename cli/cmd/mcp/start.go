package mcp

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/mcp"
)

var (
	transport string
	port      int
	debug     bool
)

func newStartCommand() *cobra.Command {
	startCmd := &cobra.Command{
		Use:   "start",
		Short: "Start the MCP server",
		Long:  "Start the Model Context Protocol server for AI assistant integration.",
		RunE:  runStartCommand,
	}

	startCmd.Flags().StringVar(&transport, "transport", "sse", "Transport mode: stdio or sse")
	startCmd.Flags().IntVar(&port, "port", 8080, "Port for SSE transport")
	startCmd.Flags().BoolVar(&debug, "debug", false, "Enable debug logging")

	return startCmd
}

func runStartCommand(cmd *cobra.Command, args []string) error {
	if debug {
		logger.SetDebug(true)
		logger.Info("Debug logging enabled")
	}

	if transport != "stdio" && transport != "sse" {
		return fmt.Errorf("invalid transport: %s (must be 'stdio' or 'sse')", transport)
	}

	if transport == "sse" && (port < 1 || port > 65535) {
		return fmt.Errorf("invalid port: %d (must be between 1 and 65535)", port)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		logger.Info("Received shutdown signal, shutting down gracefully...")
		cancel()
	}()

	server, err := mcp.NewServer(globalConfig, debug)
	if err != nil {
		return fmt.Errorf("failed to create MCP server: %w", err)
	}

	logger.Success("Starting OpenLabs MCP server with %s transport", transport)

	switch transport {
	case "stdio":
		if err := server.RunStdio(ctx); err != nil && err != context.Canceled {
			return fmt.Errorf("failed to run stdio server: %w", err)
		}
	case "sse":
		addr := fmt.Sprintf(":%d", port)
		logger.Info("MCP server listening on %s", addr)
		if err := server.RunSSE(ctx, addr); err != nil && err != context.Canceled {
			return fmt.Errorf("failed to run SSE server: %w", err)
		}
	}

	return nil
}
