package blueprints

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/output"
	"github.com/OpenLabsHQ/CLI/internal/progress"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newCreateCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "create [file]",
		Short: "Create a new blueprint",
		Long:  "Create a new range blueprint from a JSON or YAML file.",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runCreate(args[0])
		},
	}
}

func runCreate(file string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	if err := utils.ValidateFileExists(file); err != nil {
		return err
	}

	if err := utils.ValidateFileExtension(file, []string{".json", ".yaml", ".yml"}); err != nil {
		return err
	}

	var blueprintData interface{}
	if err := utils.ReadFileAsStructured(file, &blueprintData); err != nil {
		return err
	}

	spinner := progress.NewSpinner("Creating blueprint...")
	spinner.Start()

	result, err := apiClient.CreateBlueprintRange(blueprintData)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Failed to create blueprint")
		return err
	}

	progress.ShowSuccess(fmt.Sprintf("Blueprint created successfully (ID: %d)", result.ID))
	return output.Display(result, globalConfig.OutputFormat)
}
