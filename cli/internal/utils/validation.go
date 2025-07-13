package utils

import (
	"fmt"
	"net/mail"
	"os"
	"path/filepath"
	"strings"
)

func ValidateEmail(email string) error {
	if email == "" {
		return fmt.Errorf("email cannot be empty")
	}

	_, err := mail.ParseAddress(email)
	if err != nil {
		return fmt.Errorf("invalid email format: %w", err)
	}

	return nil
}

func ValidatePassword(password string) error {
	if len(password) < 8 {
		return fmt.Errorf("password must be at least 8 characters long")
	}
	return nil
}

func ValidateNonEmpty(value, fieldName string) error {
	if strings.TrimSpace(value) == "" {
		return fmt.Errorf("%s cannot be empty", fieldName)
	}
	return nil
}

func ValidateFileExists(path string) error {
	if path == "" {
		return fmt.Errorf("file path cannot be empty")
	}

	expandedPath := ExpandPath(path)
	if _, err := os.Stat(expandedPath); os.IsNotExist(err) {
		return fmt.Errorf("file does not exist: %s", path)
	}

	return nil
}

func ValidateFileExtension(path string, allowedExts []string) error {
	ext := strings.ToLower(filepath.Ext(path))
	if ext == "" {
		return fmt.Errorf("file must have an extension")
	}

	for _, allowed := range allowedExts {
		if ext == strings.ToLower(allowed) {
			return nil
		}
	}

	return fmt.Errorf("file must have one of these extensions: %s", strings.Join(allowedExts, ", "))
}

func ValidateOutputFormat(format string) error {
	validFormats := []string{"table", "json", "yaml"}

	for _, valid := range validFormats {
		if format == valid {
			return nil
		}
	}

	return fmt.Errorf("invalid output format '%s'. Valid formats: %s", format, strings.Join(validFormats, ", "))
}

func ValidatePositiveInt(value int, fieldName string) error {
	if value <= 0 {
		return fmt.Errorf("%s must be a positive integer", fieldName)
	}
	return nil
}
