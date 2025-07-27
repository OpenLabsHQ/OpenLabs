package auth

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/output"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/progress"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/utils"
)

func newSecretsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "secrets",
		Short: "Manage cloud provider credentials",
		Long:  "View and configure cloud provider credentials for deploying ranges.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runSecretsStatus()
		},
	}

	cmd.AddCommand(newSecretsAWSCommand())
	cmd.AddCommand(newSecretsAzureCommand())

	return cmd
}

func newSecretsAWSCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "aws",
		Short: "Configure AWS credentials",
		Long:  "Set up AWS access credentials for deploying ranges to AWS.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runConfigureAWS()
		},
	}
}

func newSecretsAzureCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "azure",
		Short: "Configure Azure credentials",
		Long:  "Set up Azure service principal credentials for deploying ranges to Azure.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runConfigureAzure()
		},
	}
}

func runSecretsStatus() error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	secrets, err := apiClient.GetUserSecrets()
	if err != nil {
		return fmt.Errorf("failed to get secrets status: %w", err)
	}

	if globalConfig.OutputFormat == "table" {
		displaySecretsTable(secrets)
		return nil
	}

	return output.Display(secrets, globalConfig.OutputFormat)
}

func displaySecretsTable(secrets *client.UserSecretResponse) {
	fmt.Println("Cloud Provider Credentials Status:")
	fmt.Println()

	fmt.Printf("AWS:   %s", getStatusText(secrets.AWS.HasCredentials))
	if secrets.AWS.HasCredentials && secrets.AWS.CreatedAt != nil {
		fmt.Printf(" (configured %s)", secrets.AWS.CreatedAt.Format("2006-01-02"))
	}
	fmt.Println()

	fmt.Printf("Azure: %s", getStatusText(secrets.Azure.HasCredentials))
	if secrets.Azure.HasCredentials && secrets.Azure.CreatedAt != nil {
		fmt.Printf(" (configured %s)", secrets.Azure.CreatedAt.Format("2006-01-02"))
	}
	fmt.Println()

	if !secrets.AWS.HasCredentials || !secrets.Azure.HasCredentials {
		fmt.Println()
		fmt.Println("Configure credentials with:")
		if !secrets.AWS.HasCredentials {
			fmt.Println("  openlabs auth secrets aws")
		}
		if !secrets.Azure.HasCredentials {
			fmt.Println("  openlabs auth secrets azure")
		}
	}
}

func getStatusText(hasCredentials bool) string {
	if hasCredentials {
		return "✓ Configured"
	}
	return "✗ Not configured"
}

func runConfigureAWS() error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	var accessKey, secretKey string
	var err error

	detectedCreds, detectErr := utils.DetectAWSCredentials()
	if detectErr == nil && detectedCreds != nil {
		if detectedCreds.Profile != "" {
			progress.ShowInfo(fmt.Sprintf("Found AWS credentials for %s in %s", detectedCreds.Profile, detectedCreds.Source))
		} else {
			progress.ShowInfo(fmt.Sprintf("Found AWS credentials in %s", detectedCreds.Source))
		}

		useDetected, err := utils.PromptConfirm("Use these credentials?")
		if err != nil {
			return fmt.Errorf("failed to read confirmation: %w", err)
		}

		if useDetected {
			if detectedCreds.AccessKeyID == "" {
				selectedCreds, err := utils.SelectAWSProfile()
				if err != nil {
					return fmt.Errorf("failed to select profile: %w", err)
				}
				accessKey = selectedCreds.AccessKeyID
				secretKey = selectedCreds.SecretAccessKey
			} else {
				accessKey = detectedCreds.AccessKeyID
				secretKey = detectedCreds.SecretAccessKey
			}
		}
	} else {
		progress.ShowInfo("No AWS credentials found automatically. Enter manually:")
	}

	if accessKey == "" {
		accessKey, err = utils.PromptString("AWS Access Key ID")
		if err != nil {
			return fmt.Errorf("failed to read access key: %w", err)
		}

		if err := utils.ValidateNonEmpty(accessKey, "access key"); err != nil {
			return err
		}

		secretKey, err = utils.PromptPassword("AWS Secret Access Key")
		if err != nil {
			return fmt.Errorf("failed to read secret key: %w", err)
		}

		if err := utils.ValidateNonEmpty(secretKey, "secret key"); err != nil {
			return err
		}
	}

	spinner := progress.NewSpinner("Saving AWS credentials...")
	spinner.Start()

	err = apiClient.UpdateAWSSecrets(accessKey, secretKey)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Failed to save AWS credentials")
		return err
	}

	progress.ShowSuccess("AWS credentials saved successfully")
	return nil
}

func runConfigureAzure() error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	clientID, err := utils.PromptString("Client ID")
	if err != nil {
		return fmt.Errorf("failed to read client ID: %w", err)
	}

	if err := utils.ValidateNonEmpty(clientID, "client ID"); err != nil {
		return err
	}

	clientSecret, err := utils.PromptPassword("Client Secret")
	if err != nil {
		return fmt.Errorf("failed to read client secret: %w", err)
	}

	if err := utils.ValidateNonEmpty(clientSecret, "client secret"); err != nil {
		return err
	}

	tenantID, err := utils.PromptString("Tenant ID")
	if err != nil {
		return fmt.Errorf("failed to read tenant ID: %w", err)
	}

	if err := utils.ValidateNonEmpty(tenantID, "tenant ID"); err != nil {
		return err
	}

	subscriptionID, err := utils.PromptString("Subscription ID")
	if err != nil {
		return fmt.Errorf("failed to read subscription ID: %w", err)
	}

	if err := utils.ValidateNonEmpty(subscriptionID, "subscription ID"); err != nil {
		return err
	}

	spinner := progress.NewSpinner("Saving Azure credentials...")
	spinner.Start()

	err = apiClient.UpdateAzureSecrets(clientID, clientSecret, tenantID, subscriptionID)
	spinner.Stop()

	if err != nil {
		progress.ShowError("Failed to save Azure credentials")
		return err
	}

	progress.ShowSuccess("Azure credentials saved successfully")
	return nil
}
