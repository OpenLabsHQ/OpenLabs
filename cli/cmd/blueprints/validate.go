package blueprints

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/progress"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/utils"
)

func newValidateCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "validate [file]",
		Short: "Validate a blueprint file",
		Long:  "Validate a blueprint JSON or YAML file without creating it.",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runValidate(args[0])
		},
	}
}

// Eventually, we want real validation here. Preferably local, but replicating the pydantic logic may be annoying.
func runValidate(file string) error {
	if err := utils.ValidateFileExists(file); err != nil {
		return err
	}

	if err := utils.ValidateFileExtension(file, []string{".json", ".yaml", ".yml"}); err != nil {
		return err
	}

	var blueprintData interface{}
	if err := utils.ReadFileAsStructured(file, &blueprintData); err != nil {
		return fmt.Errorf("blueprint validation failed: %w", err)
	}

	progress.ShowSuccess("Blueprint file is valid")
	return nil
}
