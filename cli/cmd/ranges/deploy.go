package ranges

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/progress"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/utils"
)

func newDeployCommand() *cobra.Command {
	var (
		name        string
		description string
		region      string
		file        string
	)

	cmd := &cobra.Command{
		Use:   "deploy [blueprint-id-or-name]",
		Short: "Deploy a cyber range",
		Long:  "Deploy a cyber range from a blueprint. Returns immediately with job ID.",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var blueprintRef string
			if len(args) > 0 {
				blueprintRef = args[0]
			}
			return runDeploy(blueprintRef, name, description, region, file)
		},
	}

	cmd.Flags().StringVarP(&name, "name", "n", "", "name for the deployed range")
	cmd.Flags().StringVarP(&description, "description", "d", "", "description for the range")
	cmd.Flags().StringVarP(&region, "region", "r", "us_east_1", "deployment region")
	cmd.Flags().StringVarP(&file, "file", "f", "", "deploy from JSON/YAML configuration file")

	return cmd
}

func runDeploy(blueprintRef, name, description, region, file string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	var request *client.DeployRangeRequest

	if file != "" {
		deployConfig, err := loadDeployConfig(file)
		if err != nil {
			return err
		}
		request = deployConfig
	} else {
		if blueprintRef == "" {
			return fmt.Errorf("blueprint ID/name is required when not using --file")
		}

		blueprintID, err := resolveBlueprintReference(apiClient, blueprintRef)
		if err != nil {
			return err
		}

		if name == "" {
			var err error
			name, err = utils.PromptString("Range name")
			if err != nil {
				return fmt.Errorf("failed to read range name: %w", err)
			}
		}

		if err := utils.ValidateNonEmpty(name, "range name"); err != nil {
			return err
		}

		request = &client.DeployRangeRequest{
			Name:        name,
			Description: description,
			BlueprintID: blueprintID,
			Region:      region,
		}
	}

	jobResponse, err := apiClient.DeployRange(request)
	if err != nil {
		return fmt.Errorf("failed to start deployment: %w", err)
	}

	progress.ShowSuccess(fmt.Sprintf("Deployment started (Job ID: %s)", jobResponse.ARQJobID))
	progress.ShowInfo("Use 'openlabs range status' to check deployment progress")

	return output.Display(jobResponse, globalConfig.OutputFormat)
}

func loadDeployConfig(file string) (*client.DeployRangeRequest, error) {
	if err := utils.ValidateFileExists(file); err != nil {
		return nil, err
	}

	if err := utils.ValidateFileExtension(file, []string{".json", ".yaml", ".yml"}); err != nil {
		return nil, err
	}

	var config client.DeployRangeRequest
	if err := utils.ReadFileAsStructured(file, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

func resolveBlueprintReference(apiClient *client.Client, ref string) (int, error) {
	if id, err := strconv.Atoi(ref); err == nil {
		return id, nil
	}

	blueprints, err := apiClient.ListBlueprintRanges()
	if err != nil {
		return 0, fmt.Errorf("failed to list blueprints: %w", err)
	}

	var matches []client.BlueprintRangeHeader
	refLower := strings.ToLower(ref)

	for _, bp := range blueprints {
		if strings.ToLower(bp.Name) == refLower {
			matches = append(matches, bp)
		}
	}

	if len(matches) == 0 {
		return 0, fmt.Errorf("no blueprint found with name '%s'", ref)
	}

	if len(matches) > 1 {
		return 0, fmt.Errorf("multiple blueprints found with name '%s'", ref)
	}

	return matches[0].ID, nil
}
