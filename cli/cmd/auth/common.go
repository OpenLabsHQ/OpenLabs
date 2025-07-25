package auth

import (
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
