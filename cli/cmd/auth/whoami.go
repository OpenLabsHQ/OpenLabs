package auth

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
)

func newWhoamiCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "whoami",
		Short: "Show current user information",
		Long:  "Display information about the currently authenticated user.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runWhoami()
		},
	}
}

func runWhoami() error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	userInfo, err := apiClient.GetUserInfo()
	if err != nil {
		return fmt.Errorf("failed to get user information: %w", err)
	}

	return output.Display(userInfo, globalConfig.OutputFormat)
}
