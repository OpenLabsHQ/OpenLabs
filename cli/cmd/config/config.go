package config

import (
	"github.com/spf13/cobra"
)

func NewConfigCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Manage CLI configuration",
		Long:  "View and modify CLI configuration settings.",
	}

	cmd.AddCommand(newShowCommand())
	cmd.AddCommand(newSetCommand())

	return cmd
}
