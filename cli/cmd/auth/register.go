package auth

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/progress"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/utils"
)

func newRegisterCommand() *cobra.Command {
	var name, email, password string

	cmd := &cobra.Command{
		Use:   "register",
		Short: "Create a new OpenLabs account",
		Long:  "Register a new user account with OpenLabs.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runRegister(cmd, name, email, password)
		},
	}

	cmd.Flags().StringVarP(&name, "name", "n", "", "full name")
	cmd.Flags().StringVarP(&email, "email", "e", "", "email address")
	cmd.Flags().StringVarP(&password, "password", "p", "", "password")

	return cmd
}

func runRegister(cmd *cobra.Command, name, email, password string) error {
	if name == "" {
		var err error
		name, err = utils.PromptString("Full name")
		if err != nil {
			return fmt.Errorf("failed to read name: %w", err)
		}
	}

	if err := utils.ValidateNonEmpty(name, "name"); err != nil {
		return err
	}

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

	if err := utils.ValidatePassword(password); err != nil {
		return err
	}

	if cmd.Flag("password").Changed {
		logger.Info("Password provided via flag - skipping confirmation")
	} else {
		confirmPassword, err := utils.PromptPassword("Confirm password")
		if err != nil {
			return fmt.Errorf("failed to read password confirmation: %w", err)
		}

		if password != confirmPassword {
			return fmt.Errorf("passwords do not match")
		}
	}

	apiClient := getClient()

	spinner := progress.NewSpinner("Creating account...")
	spinner.Start()

	err := apiClient.Register(name, email, password)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Registration failed")
		return err
	}

	progress.ShowSuccess("Account created successfully")
	progress.ShowInfo("You can now login with 'openlabs auth login'")
	return nil
}
