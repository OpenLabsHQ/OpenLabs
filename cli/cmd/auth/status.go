package auth

import (
	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/output"
)

func newStatusCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "status",
		Short: "Show authentication status",
		Long:  "Display current authentication status and API connectivity.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runStatus()
		},
	}
}

func runStatus() error {
	apiClient := getClient()

	status := map[string]interface{}{
		"authenticated": apiClient.IsAuthenticated(),
		"api_url":       globalConfig.APIURL,
	}

	if apiClient.IsAuthenticated() {
		if err := apiClient.Ping(); err != nil {
			status["api_connectivity"] = "failed"
			status["error"] = err.Error()
		} else {
			status["api_connectivity"] = "ok"
		}
	} else {
		status["api_connectivity"] = "not checked (not authenticated)"
	}

	return output.Display(status, globalConfig.OutputFormat)
}
