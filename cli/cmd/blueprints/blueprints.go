package blueprints

import (
	"github.com/spf13/cobra"
)

func NewBlueprintsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "blueprints",
		Short: "Manage range blueprints",
		Long:  "Create, list, and manage range blueprint templates.",
	}

	cmd.AddCommand(newListCommand())
	cmd.AddCommand(newShowCommand())
	cmd.AddCommand(newCreateCommand())
	cmd.AddCommand(newDeleteCommand())
	cmd.AddCommand(newValidateCommand())
	cmd.AddCommand(newExportCommand())

	return cmd
}
