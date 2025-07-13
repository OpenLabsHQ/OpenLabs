package blueprints

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/output"
)

func newListCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List available blueprints",
		Long:  "Show all available range blueprints.",
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

	blueprints, err := apiClient.ListBlueprintRanges()
	if err != nil {
		return fmt.Errorf("failed to list blueprints: %w", err)
	}

	if len(blueprints) == 0 {
		fmt.Println("No blueprints found. Create one with 'openlabs blueprints create'")
		return nil
	}

	return output.Display(blueprints, globalConfig.OutputFormat)
}
