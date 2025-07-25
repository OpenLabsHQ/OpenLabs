package ranges

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
)

func newListCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List deployed ranges",
		Long:  "Show all deployed ranges for the current user.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runList()
		},
	}
}

func runList() error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	ranges, err := apiClient.ListRanges()
	if err != nil {
		return fmt.Errorf("failed to list ranges: %w", err)
	}

	if len(ranges) == 0 {
		fmt.Println("No ranges found. Deploy one with 'openlabs range deploy'")
		return nil
	}

	return output.Display(ranges, globalConfig.OutputFormat)
}
