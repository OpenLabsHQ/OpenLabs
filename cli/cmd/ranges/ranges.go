package ranges

import (
	"github.com/spf13/cobra"
)

func NewRangeCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "range",
		Short: "Manage cyber ranges",
		Long:  "Deploy, monitor, and manage cyber range infrastructure.",
	}

	cmd.AddCommand(newListCommand())
	cmd.AddCommand(newStatusCommand())
	cmd.AddCommand(newDeployCommand())
	cmd.AddCommand(newDestroyCommand())
	cmd.AddCommand(newKeyCommand())
	cmd.AddCommand(newJobsCommand())

	return cmd
}
