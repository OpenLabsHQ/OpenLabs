package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type Config struct {
	APIURL        string        `json:"api_url"`
	AuthToken     string        `json:"auth_token"`
	EncryptionKey string        `json:"encryption_key"`
	OutputFormat  string        `json:"output_format"`
	Timeout       time.Duration `json:"timeout"`
	SSHKeyPath    string        `json:"ssh_key_path"`
	Debug         bool          `json:"debug"`
}

func DefaultConfig() *Config {
	homeDir, _ := os.UserHomeDir()
	return &Config{
		APIURL:       "https://api.openlabs.sh",
		OutputFormat: "table",
		Timeout:      5 * time.Minute,
		SSHKeyPath:   filepath.Join(homeDir, ".openlabs", "keys"),
		Debug:        false,
	}
}

func Load() (*Config, error) {
	configPath, err := getConfigPath()
	if err != nil {
		return nil, err
	}

	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		config := DefaultConfig()
		if err := config.Save(); err != nil {
			return nil, err
		}
		return config, nil
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	return &config, nil
}

func LoadFromPath(configPath string) (*Config, error) {
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("config file does not exist: %s", configPath)
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	return &config, nil
}

func (c *Config) Save() error {
	configPath, err := getConfigPath()
	if err != nil {
		return err
	}

	if err := ensureConfigDir(); err != nil {
		return err
	}

	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	return os.WriteFile(configPath, data, 0600)
}

func (c *Config) SetAPIURL(url string) error {
	c.APIURL = url
	return c.Save()
}

func (c *Config) SetOutputFormat(format string) error {
	validFormats := map[string]bool{
		"table": true,
		"json":  true,
		"yaml":  true,
	}

	if !validFormats[format] {
		return fmt.Errorf("invalid output format: %s (valid: table, json, yaml)", format)
	}

	c.OutputFormat = format
	return c.Save()
}

func (c *Config) SetCredentials(authToken, encryptionKey string) error {
	c.AuthToken = authToken
	c.EncryptionKey = encryptionKey
	return c.Save()
}

func (c *Config) ClearCredentials() error {
	c.AuthToken = ""
	c.EncryptionKey = ""
	return c.Save()
}

func getConfigDir() (string, error) {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("failed to get home directory: %w", err)
	}
	return filepath.Join(homeDir, ".openlabs"), nil
}

func getConfigPath() (string, error) {
	configDir, err := getConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(configDir, "config.json"), nil
}

func ensureConfigDir() error {
	configDir, err := getConfigDir()
	if err != nil {
		return err
	}

	if _, err := os.Stat(configDir); os.IsNotExist(err) {
		return os.MkdirAll(configDir, 0755)
	}

	return nil
}

func GetConfigPath() (string, error) {
	return getConfigPath()
}
