package ranges

import (
	"fmt"

	"github.com/spf13/cobra"
)

func newStatusCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "status [range-id]",
		Short: "Show range status",
		Long:  "Display concise status information about a deployed range.",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var rangeID string
			if len(args) > 0 {
				rangeID = args[0]
			}
			return runStatus(rangeID)
		},
	}
}

func runStatus(rangeIDStr string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	rangeID, err := resolveRangeID(apiClient, rangeIDStr)
	if err != nil {
		return err
	}

	rangeData, err := apiClient.GetRange(rangeID)
	if err != nil {
		return fmt.Errorf("failed to get range details: %w", err)
	}

	// Display concise status
	fmt.Printf("Range: %s (ID: %d)\n", rangeData.Name, rangeData.ID)
	fmt.Printf("State: %s\n", rangeData.State)
	if rangeData.Description != "" {
		fmt.Printf("Description: %s\n", rangeData.Description)
	}
	fmt.Printf("Region: %s\n", rangeData.Region)

	// Count hosts
	totalHosts := 0
	for _, vpc := range rangeData.VPCs {
		for _, subnet := range vpc.Subnets {
			totalHosts += len(subnet.Hosts)
		}
	}
	fmt.Printf("Hosts: %d\n", totalHosts)

	fmt.Printf("Created: %s\n", rangeData.Date.Format("2006-01-02 15:04:05"))

	return nil
}
