package cmd

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/cmd/auth"
	"github.com/OpenLabsHQ/OpenLabs/cli/cmd/blueprints"
	"github.com/OpenLabsHQ/OpenLabs/cli/cmd/config"
	"github.com/OpenLabsHQ/OpenLabs/cli/cmd/ranges"
	internalConfig "github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
)

var (
	globalConfig *internalConfig.Config
	configPath   string
	outputFormat string
	apiURL       string
	verbose      bool
	version      string = "dev" // Set by ldflags during build
)

var rootCmd = &cobra.Command{
	Use:           "openlabs",
	Short:         "OpenLabs is a CLI for managing the OpenLabs API",
	Long:          "OpenLabs CLI provides commands for managing cyber ranges, blueprints, and cloud infrastructure.",
	Version:       getVersion(),
	SilenceUsage:  false,
	SilenceErrors: true,
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		if err := initializeGlobalConfig(); err != nil {
			return fmt.Errorf("failed to initialize configuration: %w", err)
		}

		applyGlobalFlags()
		return nil
	},
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		handleError(err, rootCmd)
		os.Exit(1)
	}
}

func handleError(err error, cmd *cobra.Command) {
	if isUsageError(err) {
		fmt.Fprintf(os.Stderr, "Error: %s\n\nRun 'openlabs --help' for usage.\n", err.Error())
	} else {
		output.DisplayError(err)
	}
}

func isUsageError(err error) bool {
	errStr := err.Error()
	usageErrors := []string{
		"unknown command",
		"unknown flag",
		"flag needs an argument",
		"invalid argument",
		"accepts",
		"requires",
		"unknown shorthand flag",
		"required flag",
	}

	for _, usageErr := range usageErrors {
		if strings.Contains(errStr, usageErr) {
			return true
		}
	}

	return false
}

func init() {
	setupGlobalFlags()
	addSubcommands()
}

func setupGlobalFlags() {
	rootCmd.PersistentFlags().StringVar(&configPath, "config", "", "config file path (default: ~/.openlabs/config.json)")
	rootCmd.PersistentFlags().StringVar(&outputFormat, "format", "", "output format (table, json, yaml)")
	rootCmd.PersistentFlags().StringVar(&apiURL, "api-url", "", "OpenLabs API URL")
	rootCmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "enable verbose output")
}

func addSubcommands() {
	rootCmd.AddCommand(auth.NewAuthCommand())
	rootCmd.AddCommand(ranges.NewRangeCommand())
	rootCmd.AddCommand(blueprints.NewBlueprintsCommand())
	rootCmd.AddCommand(config.NewConfigCommand())
}

func initializeGlobalConfig() error {
	var err error

	if configPath != "" {
		globalConfig, err = loadConfigFromPath(configPath)
	} else {
		globalConfig, err = internalConfig.Load()
	}

	if err != nil {
		return err
	}

	return nil
}

func applyGlobalFlags() {
	if apiURL != "" {
		globalConfig.APIURL = apiURL
	}

	if outputFormat != "" {
		globalConfig.OutputFormat = outputFormat
	}

	if verbose {
		globalConfig.Debug = true
	}

	// Set logger level based on debug flag
	logger.SetDebug(globalConfig.Debug)

	auth.SetGlobalConfig(globalConfig)
	ranges.SetGlobalConfig(globalConfig)
	blueprints.SetGlobalConfig(globalConfig)
}

func loadConfigFromPath(path string) (*internalConfig.Config, error) {
	return internalConfig.LoadFromPath(path)
}

func GetGlobalConfig() *internalConfig.Config {
	return globalConfig
}

func getVersion() string {
	return version
}
