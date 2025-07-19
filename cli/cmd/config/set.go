package config

import (
	"fmt"

	"github.com/spf13/cobra"

	internalConfig "github.com/OpenLabsHQ/CLI/internal/config"
	"github.com/OpenLabsHQ/CLI/internal/progress"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newSetCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "set [key] [value]",
		Short: "Set configuration value",
		Long:  "Set a configuration value. Available keys: api-url, format",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runSet(args[0], args[1])
		},
	}

	return cmd
}

func runSet(key, value string) error {
	config, err := internalConfig.Load()
	if err != nil {
		return fmt.Errorf("failed to load configuration: %w", err)
	}

	switch key {
	case "api-url":
		if err := config.SetAPIURL(value); err != nil {
			return err
		}
		progress.ShowSuccess(fmt.Sprintf("API URL set to: %s", value))

	case "format":
		if err := utils.ValidateOutputFormat(value); err != nil {
			return err
		}
		if err := config.SetOutputFormat(value); err != nil {
			return err
		}
		progress.ShowSuccess(fmt.Sprintf("Output format set to: %s", value))

	default:
		return fmt.Errorf("unknown configuration key: %s (valid: api-url, format)", key)
	}

	return nil
}
