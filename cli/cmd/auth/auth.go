package auth

import (
	"github.com/spf13/cobra"
)

func NewAuthCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "auth",
		Short: "Manage authentication and user account",
		Long:  "Commands for login, logout, registration, and managing cloud provider credentials.",
	}

	cmd.AddCommand(newLoginCommand())
	cmd.AddCommand(newLogoutCommand())
	cmd.AddCommand(newRegisterCommand())
	cmd.AddCommand(newStatusCommand())
	cmd.AddCommand(newWhoamiCommand())
	cmd.AddCommand(newPasswordCommand())
	cmd.AddCommand(newSecretsCommand())

	return cmd
}
