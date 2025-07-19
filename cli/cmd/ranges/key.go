package ranges

import (
	"fmt"

	"github.com/spf13/cobra"
)

func newKeyCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "key [range-id]",
		Short: "Get SSH private key for range",
		Long:  "Retrieve and save the SSH private key for connecting to range hosts.",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var rangeID string
			if len(args) > 0 {
				rangeID = args[0]
			}
			return runKey(rangeID)
		},
	}
}

func runKey(rangeIDStr string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	rangeID, err := resolveRangeID(apiClient, rangeIDStr)
	if err != nil {
		return err
	}

	keyResponse, err := apiClient.GetRangeKey(rangeID)
	if err != nil {
		return fmt.Errorf("failed to get range key: %w", err)
	}

	fmt.Println(keyResponse.RangePrivateKey)
	return nil
}
