package blueprints

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
)

func newShowCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "show [blueprint-id]",
		Short: "Show blueprint details",
		Long:  "Display detailed information about a specific blueprint.",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runShow(args[0])
		},
	}
}

func runShow(blueprintIDStr string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	blueprintID, err := strconv.Atoi(blueprintIDStr)
	if err != nil {
		return fmt.Errorf("invalid blueprint ID: %s", blueprintIDStr)
	}

	blueprint, err := apiClient.GetBlueprintRange(blueprintID)
	if err != nil {
		return fmt.Errorf("failed to get blueprint: %w", err)
	}

	if globalConfig.OutputFormat == "table" {
		displayBlueprintTable(blueprint)
		return nil
	}

	return output.Display(blueprint, globalConfig.OutputFormat)
}

func displayBlueprintTable(blueprint *client.BlueprintRange) {
	fmt.Printf("Blueprint #%d: %s\n", blueprint.ID, blueprint.Name)
	if blueprint.Description != "" {
		fmt.Printf("Description: %s\n", blueprint.Description)
	}
	fmt.Printf("Provider: %s\n", blueprint.Provider)
	fmt.Printf("VNC: %t, VPN: %t\n\n", blueprint.VNC, blueprint.VPN)

	for _, vpc := range blueprint.VPCs {
		fmt.Printf("VPC: %s (%s)\n", vpc.Name, vpc.CIDR)

		for _, subnet := range vpc.Subnets {
			fmt.Printf("  └─ Subnet: %s (%s)\n", subnet.Name, subnet.CIDR)

			for _, host := range subnet.Hosts {
				tags := ""
				if len(host.Tags) > 0 {
					tags = fmt.Sprintf(" [%s]", strings.Join(host.Tags, ", "))
				}
				fmt.Printf("     └─ Host: %s (%s, %s, %dGB)%s\n",
					host.Hostname, host.OS, host.Spec, host.Size, tags)
			}
			if len(subnet.Hosts) == 0 {
				fmt.Printf("     └─ (no hosts)\n")
			}
		}
		if len(vpc.Subnets) == 0 {
			fmt.Printf("  └─ (no subnets)\n")
		}
		fmt.Println()
	}

	if len(blueprint.VPCs) == 0 {
		fmt.Println("(no VPCs defined)")
	}
}
