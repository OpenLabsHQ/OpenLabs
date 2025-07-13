package utils

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/aws/aws-sdk-go-v2/config"
)

type AWSCredentials struct {
	AccessKeyID     string
	SecretAccessKey string
	Source          string
	Profile         string
}

type AWSProfile struct {
	Name            string
	AccessKeyID     string
	SecretAccessKey string
}

func DetectAWSCredentials() (*AWSCredentials, error) {
	if os.Getenv("AWS_ACCESS_KEY_ID") != "" {
		ctx := context.Background()
		cfg, err := config.LoadDefaultConfig(ctx)
		if err != nil {
			return nil, err
		}

		creds, err := cfg.Credentials.Retrieve(ctx)
		if err != nil {
			return nil, err
		}

		return &AWSCredentials{
			AccessKeyID:     creds.AccessKeyID,
			SecretAccessKey: creds.SecretAccessKey,
			Source:          "environment variables",
			Profile:         "default",
		}, nil
	}

	profiles, err := parseAWSProfiles()
	if err != nil {
		return nil, err
	}

	if len(profiles) == 0 {
		return nil, nil
	}

	if len(profiles) == 1 {
		profile := profiles[0]
		return &AWSCredentials{
			AccessKeyID:     profile.AccessKeyID,
			SecretAccessKey: profile.SecretAccessKey,
			Source:          "~/.aws/credentials",
			Profile:         profile.Name,
		}, nil
	}

	return &AWSCredentials{
		Source:  "~/.aws/credentials",
		Profile: fmt.Sprintf("%d profiles", len(profiles)),
	}, nil
}

func SelectAWSProfile() (*AWSCredentials, error) {
	profiles, err := parseAWSProfiles()
	if err != nil {
		return nil, err
	}

	if len(profiles) == 0 {
		return nil, fmt.Errorf("no profiles found")
	}

	fmt.Println("Select AWS profile:")
	for i, profile := range profiles {
		fmt.Printf("  %d. %s\n", i+1, profile.Name)
	}

	choice, err := PromptString("Profile number")
	if err != nil {
		return nil, err
	}

	profileIndex := 0
	if _, err := fmt.Sscanf(choice, "%d", &profileIndex); err != nil || profileIndex < 1 || profileIndex > len(profiles) {
		return nil, fmt.Errorf("invalid selection: %s", choice)
	}

	selectedProfile := profiles[profileIndex-1]
	return &AWSCredentials{
		AccessKeyID:     selectedProfile.AccessKeyID,
		SecretAccessKey: selectedProfile.SecretAccessKey,
		Source:          "~/.aws/credentials",
		Profile:         selectedProfile.Name,
	}, nil
}

func parseAWSProfiles() ([]AWSProfile, error) {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}

	credentialsPath := filepath.Join(homeDir, ".aws", "credentials")
	file, err := os.Open(credentialsPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var profiles []AWSProfile
	var currentProfile *AWSProfile

	profileRegex := regexp.MustCompile(`^\[(.+)\]$`)
	scanner := bufio.NewScanner(file)

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		if matches := profileRegex.FindStringSubmatch(line); matches != nil {
			if currentProfile != nil && currentProfile.AccessKeyID != "" && currentProfile.SecretAccessKey != "" {
				profiles = append(profiles, *currentProfile)
			}
			currentProfile = &AWSProfile{Name: matches[1]}
			continue
		}

		if currentProfile != nil && strings.Contains(line, "=") {
			parts := strings.SplitN(line, "=", 2)
			key := strings.TrimSpace(parts[0])
			value := strings.TrimSpace(parts[1])

			switch key {
			case "aws_access_key_id":
				currentProfile.AccessKeyID = value
			case "aws_secret_access_key":
				currentProfile.SecretAccessKey = value
			}
		}
	}

	if currentProfile != nil && currentProfile.AccessKeyID != "" && currentProfile.SecretAccessKey != "" {
		profiles = append(profiles, *currentProfile)
	}

	return profiles, scanner.Err()
}
