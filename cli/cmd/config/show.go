package config

import (
	"fmt"

	"github.com/spf13/cobra"

	internalConfig "github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
)

func newShowCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "show",
		Short: "Show current configuration",
		Long:  "Display the current CLI configuration settings.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runShow()
		},
	}
}

func runShow() error {
	config, err := internalConfig.Load()
	if err != nil {
		return fmt.Errorf("failed to load configuration: %w", err)
	}

	displayConfig := map[string]interface{}{
		"api_url":       config.APIURL,
		"output_format": config.OutputFormat,
		"timeout":       config.Timeout.String(),
		"ssh_key_path":  config.SSHKeyPath,
		"debug":         config.Debug,
		"authenticated": config.AuthToken != "",
	}

	return output.Display(displayConfig, config.OutputFormat)
}
