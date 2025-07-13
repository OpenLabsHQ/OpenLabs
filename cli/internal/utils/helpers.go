package utils

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"strings"
	"syscall"

	"golang.org/x/term"
	"gopkg.in/yaml.v3"
)

func ExpandPath(path string) string {
	if strings.HasPrefix(path, "~/") {
		usr, err := user.Current()
		if err != nil {
			return path
		}
		return filepath.Join(usr.HomeDir, path[2:])
	}
	return path
}

func ReadFileAsJSON(path string, target interface{}) error {
	expandedPath := ExpandPath(path)
	data, err := os.ReadFile(expandedPath)
	if err != nil {
		return fmt.Errorf("failed to read file %s: %w", path, err)
	}

	if err := json.Unmarshal(data, target); err != nil {
		return fmt.Errorf("failed to parse JSON from %s: %w", path, err)
	}

	return nil
}

func ReadFileAsYAML(path string, target interface{}) error {
	expandedPath := ExpandPath(path)
	data, err := os.ReadFile(expandedPath)
	if err != nil {
		return fmt.Errorf("failed to read file %s: %w", path, err)
	}

	if err := yaml.Unmarshal(data, target); err != nil {
		return fmt.Errorf("failed to parse YAML from %s: %w", path, err)
	}

	return nil
}

func ReadFileAsStructured(path string, target interface{}) error {
	ext := strings.ToLower(filepath.Ext(path))

	switch ext {
	case ".json":
		return ReadFileAsJSON(path, target)
	case ".yaml", ".yml":
		return ReadFileAsYAML(path, target)
	default:
		return fmt.Errorf("unsupported file format: %s (supported: .json, .yaml, .yml)", ext)
	}
}

func WriteJSONToFile(path string, data interface{}) error {
	expandedPath := ExpandPath(path)

	if err := os.MkdirAll(filepath.Dir(expandedPath), 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal JSON: %w", err)
	}

	if err := os.WriteFile(expandedPath, jsonData, 0600); err != nil {
		return fmt.Errorf("failed to write file %s: %w", path, err)
	}

	return nil
}

func WriteYAMLToFile(path string, data interface{}) error {
	expandedPath := ExpandPath(path)

	if err := os.MkdirAll(filepath.Dir(expandedPath), 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	yamlData, err := yaml.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal YAML: %w", err)
	}

	if err := os.WriteFile(expandedPath, yamlData, 0600); err != nil {
		return fmt.Errorf("failed to write file %s: %w", path, err)
	}

	return nil
}

func PromptString(prompt string) (string, error) {
	fmt.Print(prompt + ": ")

	reader := bufio.NewReader(os.Stdin)
	input, err := reader.ReadString('\n')
	if err != nil {
		return "", fmt.Errorf("failed to read input: %w", err)
	}

	return strings.TrimSpace(input), nil
}

func PromptPassword(prompt string) (string, error) {
	fmt.Print(prompt + ": ")

	password, err := term.ReadPassword(int(syscall.Stdin))
	fmt.Println()

	if err != nil {
		return "", fmt.Errorf("failed to read password: %w", err)
	}

	return string(password), nil
}

func PromptConfirm(prompt string) (bool, error) {
	for {
		response, err := PromptString(prompt + " (y/N)")
		if err != nil {
			return false, err
		}

		response = strings.ToLower(strings.TrimSpace(response))
		switch response {
		case "y", "yes":
			return true, nil
		case "n", "no", "":
			return false, nil
		default:
			fmt.Println("Please answer 'y' or 'n'")
		}
	}
}

func EnsureDirectory(path string) error {
	expandedPath := ExpandPath(path)
	return os.MkdirAll(expandedPath, 0755)
}

func TruncateString(s string, maxLength int) string {
	if len(s) <= maxLength {
		return s
	}

	if maxLength <= 3 {
		return s[:maxLength]
	}

	return s[:maxLength-3] + "..."
}
