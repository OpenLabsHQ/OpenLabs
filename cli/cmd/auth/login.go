package auth

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/progress"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newLoginCommand() *cobra.Command {
	var email, password string

	cmd := &cobra.Command{
		Use:   "login",
		Short: "Login to OpenLabs",
		Long:  "Authenticate with OpenLabs API and store credentials securely.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runLogin(email, password)
		},
	}

	cmd.Flags().StringVarP(&email, "email", "e", "", "email address")
	cmd.Flags().StringVarP(&password, "password", "p", "", "password")

	return cmd
}

func runLogin(email, password string) error {
	if email == "" {
		var err error
		email, err = utils.PromptString("Email")
		if err != nil {
			return fmt.Errorf("failed to read email: %w", err)
		}
	}

	if err := utils.ValidateEmail(email); err != nil {
		return err
	}

	if password == "" {
		var err error
		password, err = utils.PromptPassword("Password")
		if err != nil {
			return fmt.Errorf("failed to read password: %w", err)
		}
	}

	apiClient := getClient()

	spinner := progress.NewSpinner("Authenticating...")
	spinner.Start()

	err := apiClient.Login(email, password)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Authentication failed")
		return err
	}

	progress.ShowSuccess("Successfully logged in")
	return nil
}
