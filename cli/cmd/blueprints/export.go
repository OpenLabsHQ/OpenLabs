package blueprints

import (
	"fmt"
	"strconv"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/progress"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/utils"
)

func newExportCommand() *cobra.Command {
	var outputFile string
	var format string

	cmd := &cobra.Command{
		Use:   "export [blueprint-id]",
		Short: "Export a blueprint to file",
		Long:  "Export an existing blueprint to a JSON or YAML file.",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runExport(args[0], outputFile, format)
		},
	}

	cmd.Flags().StringVarP(&outputFile, "output", "o", "", "output file path (required)")
	cmd.Flags().StringVarP(&format, "format", "f", "json", "output format (json or yaml)")
	_ = cmd.MarkFlagRequired("output")

	return cmd
}

func runExport(blueprintIDStr, outputFile, format string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	blueprintID, err := strconv.Atoi(blueprintIDStr)
	if err != nil {
		return fmt.Errorf("invalid blueprint ID: %s", blueprintIDStr)
	}

	if format != "json" && format != "yaml" {
		return fmt.Errorf("invalid format: %s (valid: json, yaml)", format)
	}

	blueprint, err := apiClient.GetBlueprintRange(blueprintID)
	if err != nil {
		return fmt.Errorf("failed to get blueprint: %w", err)
	}

	spinner := progress.NewSpinner("Exporting blueprint...")
	spinner.Start()

	var writeErr error
	if format == "json" {
		writeErr = utils.WriteJSONToFile(outputFile, blueprint)
	} else {
		writeErr = utils.WriteYAMLToFile(outputFile, blueprint)
	}

	spinner.Stop()

	if writeErr != nil {
		progress.ShowError("Failed to export blueprint")
		return writeErr
	}

	progress.ShowSuccess(fmt.Sprintf("Blueprint exported to %s", outputFile))
	return nil
}
