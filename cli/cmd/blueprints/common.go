package blueprints

import (
	"github.com/OpenLabsHQ/CLI/internal/client"
	"github.com/OpenLabsHQ/CLI/internal/config"
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
