package auth

import (
	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/progress"
)

func newLogoutCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "logout",
		Short: "Logout from OpenLabs",
		Long:  "Clear stored authentication credentials and logout from the API.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runLogout()
		},
	}
}

func runLogout() error {
	apiClient := getClient()

	spinner := progress.NewSpinner("Logging out...")
	spinner.Start()

	err := apiClient.Logout()
	spinner.Stop()

	if err != nil {
		progress.ShowError("Logout failed")
		return err
	}

	progress.ShowSuccess("Successfully logged out")
	return nil
}
