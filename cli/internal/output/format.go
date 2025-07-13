package output

import (
	"encoding/json"
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

type Formatter interface {
	Format(data interface{}) (string, error)
}

type TableFormatter struct{}
type JSONFormatter struct{}
type YAMLFormatter struct{}

func NewFormatter(format string) Formatter {
	switch format {
	case "json":
		return &JSONFormatter{}
	case "yaml":
		return &YAMLFormatter{}
	default:
		return &TableFormatter{}
	}
}

func (f *JSONFormatter) Format(data interface{}) (string, error) {
	output, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to format as JSON: %w", err)
	}
	return string(output), nil
}

func (f *YAMLFormatter) Format(data interface{}) (string, error) {
	output, err := yaml.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("failed to format as YAML: %w", err)
	}
	return string(output), nil
}

func (f *TableFormatter) Format(data interface{}) (string, error) {
	return formatAsTable(data)
}

func Display(data interface{}, format string) error {
	formatter := NewFormatter(format)
	output, err := formatter.Format(data)
	if err != nil {
		return err
	}

	fmt.Fprint(os.Stdout, output)
	return nil
}

func DisplayError(err error) {
	fmt.Fprintf(os.Stderr, "Error: %v\n", err)
}
