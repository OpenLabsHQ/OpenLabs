package auth

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/progress"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newPasswordCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "password",
		Short: "Change account password",
		Long:  "Change your OpenLabs account password.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runPasswordChange()
		},
	}
}

func runPasswordChange() error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	currentPassword, err := utils.PromptPassword("Current password")
	if err != nil {
		return fmt.Errorf("failed to read current password: %w", err)
	}

	newPassword, err := utils.PromptPassword("New password")
	if err != nil {
		return fmt.Errorf("failed to read new password: %w", err)
	}

	if err := utils.ValidatePassword(newPassword); err != nil {
		return err
	}

	confirmPassword, err := utils.PromptPassword("Confirm new password")
	if err != nil {
		return fmt.Errorf("failed to read password confirmation: %w", err)
	}

	if newPassword != confirmPassword {
		return fmt.Errorf("passwords do not match")
	}

	spinner := progress.NewSpinner("Updating password...")
	spinner.Start()

	err = apiClient.UpdatePassword(currentPassword, newPassword)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Password update failed")
		return err
	}

	progress.ShowSuccess("Password updated successfully")
	return nil
}
