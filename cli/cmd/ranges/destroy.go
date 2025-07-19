package ranges

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/progress"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newDestroyCommand() *cobra.Command {
	var force bool

	cmd := &cobra.Command{
		Use:   "destroy [range-id]",
		Short: "Destroy a deployed range",
		Long:  "Permanently destroy a deployed range and all its resources. Returns immediately with job ID.",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var rangeID string
			if len(args) > 0 {
				rangeID = args[0]
			}
			return runDestroy(rangeID, force)
		},
	}

	cmd.Flags().BoolVarP(&force, "force", "f", false, "skip confirmation prompt")

	return cmd
}

func runDestroy(rangeIDStr string, force bool) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	rangeID, err := resolveRangeID(apiClient, rangeIDStr)
	if err != nil {
		return err
	}

	if !force {
		confirmed, err := utils.PromptConfirm(fmt.Sprintf("Are you sure you want to destroy range %d?", rangeID))
		if err != nil {
			return err
		}
		if !confirmed {
			progress.ShowInfo("Destroy cancelled")
			return nil
		}
	}

	jobResponse, err := apiClient.DeleteRange(rangeID)
	if err != nil {
		return fmt.Errorf("failed to start destruction: %w", err)
	}

	progress.ShowSuccess(fmt.Sprintf("Destruction started (Job ID: %s)", jobResponse.ARQJobID))
	progress.ShowInfo("Use 'openlabs range status' to check destruction progress")

	return nil
}
