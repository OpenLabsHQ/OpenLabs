package ranges

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
)

var globalConfig *config.Config

func SetGlobalConfig(cfg *config.Config) {
	globalConfig = cfg
}

func getClient() *client.Client {
	if globalConfig == nil {
		cfg, _ := config.Load()
		globalConfig = cfg
	}
	return client.New(globalConfig)
}

func resolveRangeID(apiClient *client.Client, idStr string) (int, error) {
	if idStr == "" {
		ranges, err := apiClient.ListRanges()
		if err != nil {
			return 0, fmt.Errorf("failed to list ranges: %w", err)
		}

		if len(ranges) == 0 {
			return 0, fmt.Errorf("no ranges found")
		}

		if len(ranges) == 1 {
			return ranges[0].ID, nil
		}

		return 0, fmt.Errorf("multiple ranges found, please specify range ID")
	}

	if id, err := strconv.Atoi(idStr); err == nil {
		return id, nil
	}

	ranges, err := apiClient.ListRanges()
	if err != nil {
		return 0, fmt.Errorf("failed to list ranges: %w", err)
	}

	var matches []client.DeployedRangeHeader
	nameLower := strings.ToLower(idStr)

	for _, r := range ranges {
		if strings.ToLower(r.Name) == nameLower {
			matches = append(matches, r)
		}
	}

	if len(matches) == 0 {
		return 0, fmt.Errorf("no range found with name '%s'", idStr)
	}

	if len(matches) > 1 {
		return 0, fmt.Errorf("multiple ranges found with name '%s'", idStr)
	}

	return matches[0].ID, nil
}
