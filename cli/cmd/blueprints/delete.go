package blueprints

import (
	"fmt"
	"strconv"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/progress"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newDeleteCommand() *cobra.Command {
	var force bool

	cmd := &cobra.Command{
		Use:   "delete [blueprint-id]",
		Short: "Delete a blueprint",
		Long:  "Permanently delete a range blueprint.",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runDelete(args[0], force)
		},
	}

	cmd.Flags().BoolVarP(&force, "force", "f", false, "skip confirmation prompt")
	return cmd
}

func runDelete(blueprintIDStr string, force bool) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	blueprintID, err := strconv.Atoi(blueprintIDStr)
	if err != nil {
		return fmt.Errorf("invalid blueprint ID: %s", blueprintIDStr)
	}

	if !force {
		confirmed, err := utils.PromptConfirm(fmt.Sprintf("Are you sure you want to delete blueprint %d?", blueprintID))
		if err != nil {
			return err
		}
		if !confirmed {
			progress.ShowInfo("Delete cancelled")
			return nil
		}
	}

	spinner := progress.NewSpinner("Deleting blueprint...")
	spinner.Start()

	err = apiClient.DeleteBlueprintRange(blueprintID)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Failed to delete blueprint")
		return err
	}

	progress.ShowSuccess(fmt.Sprintf("Blueprint %d deleted successfully", blueprintID))
	return nil
}
