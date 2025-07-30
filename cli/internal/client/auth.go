package client

import (
	"fmt"
	"net/http"
	"net/url"

	"github.com/OpenLabsHQ/CLI/internal/logger"
)

func (c *Client) Login(email, password string) error {
	credentials := UserCredentials{
		Email:    email,
		Password: password,
	}

	var response LoginResponse
	var authToken, encKey string

	cookieHandler := func(cookies []*http.Cookie) {
		for _, cookie := range cookies {
			switch cookie.Name {
			case "token", "access_token_cookie", "jwt", "auth_token", "access_token":
				authToken = cookie.Value
			case "enc_key":
				encKey = cookie.Value
			}
		}
	}

	if err := c.makeRequestWithCookies("POST", "/api/v1/auth/login", credentials, &response, cookieHandler); err != nil {
		return fmt.Errorf("login failed: %w", err)
	}

	if !response.Success {
		return fmt.Errorf("login failed: invalid credentials")
	}

	logger.Debug("Captured authentication cookies successfully")

	if authToken == "" {
		return fmt.Errorf("no authentication token received from server")
	}

	if err := c.config.SetCredentials(authToken, encKey); err != nil {
		return fmt.Errorf("failed to save credentials: %w", err)
	}

	return nil
}

func (c *Client) Logout() error {
	if err := c.makeRequest("POST", "/api/v1/auth/logout", nil, nil); err != nil {
		return fmt.Errorf("logout request failed: %w", err)
	}

	if err := c.config.ClearCredentials(); err != nil {
		return fmt.Errorf("failed to clear stored credentials: %w", err)
	}

	return nil
}

func (c *Client) Register(name, email, password string) error {
	registration := UserRegistration{
		Name:     name,
		Email:    email,
		Password: password,
	}

	var response struct {
		ID int `json:"id"`
	}

	if err := c.makeRequest("POST", "/api/v1/auth/register", registration, &response); err != nil {
		return fmt.Errorf("registration failed: %w", err)
	}

	return nil
}

func (c *Client) GetUserInfo() (*UserInfo, error) {
	var userInfo UserInfo
	if err := c.makeRequest("GET", "/api/v1/users/me", nil, &userInfo); err != nil {
		return nil, fmt.Errorf("failed to get user info: %w", err)
	}
	return &userInfo, nil
}

func (c *Client) UpdatePassword(currentPassword, newPassword string) error {
	passwordUpdate := PasswordUpdate{
		CurrentPassword: currentPassword,
		NewPassword:     newPassword,
	}

	var response Message
	if err := c.makeRequest("POST", "/api/v1/users/me/password", passwordUpdate, &response); err != nil {
		return fmt.Errorf("password update failed: %w", err)
	}

	cookies := c.extractAuthCookies()
	if cookies.AuthToken != "" {
		_ = c.config.SetCredentials(cookies.AuthToken, cookies.EncryptionKey)
	}

	return nil
}

func (c *Client) GetUserSecrets() (*UserSecretResponse, error) {
	var secrets UserSecretResponse
	if err := c.makeRequest("GET", "/api/v1/users/me/secrets", nil, &secrets); err != nil {
		return nil, fmt.Errorf("failed to get user secrets: %w", err)
	}
	return &secrets, nil
}

type AWSCredentials struct {
	AccessKey string `json:"aws_access_key"`
	SecretKey string `json:"aws_secret_key"`
}

type AWSSecretsPayload struct {
	Provider    string         `json:"provider"`
	Credentials AWSCredentials `json:"credentials"`
}

type AzureCredentials struct {
	ClientID       string `json:"azure_client_id"`
	ClientSecret   string `json:"azure_client_secret"`
	TenantID       string `json:"azure_tenant_id"`
	SubscriptionID string `json:"azure_subscription_id"`
}

type AzureSecretsPayload struct {
	Provider    string           `json:"provider"`
	Credentials AzureCredentials `json:"credentials"`
}

func (c *Client) UpdateAWSSecrets(accessKey, secretKey string) error {
	payload := AWSSecretsPayload{
		Provider: "aws",
		Credentials: AWSCredentials{
			AccessKey: accessKey,
			SecretKey: secretKey,
		},
	}

	var response Message
	if err := c.makeRequest("POST", "/api/v1/users/me/secrets", payload, &response); err != nil {
		return fmt.Errorf("failed to update AWS secrets: %w", err)
	}

	return nil
}

func (c *Client) UpdateAzureSecrets(clientID, clientSecret, tenantID, subscriptionID string) error {
	payload := AzureSecretsPayload{
		Provider: "azure",
		Credentials: AzureCredentials{
			ClientID:       clientID,
			ClientSecret:   clientSecret,
			TenantID:       tenantID,
			SubscriptionID: subscriptionID,
		},
	}

	var response Message
	if err := c.makeRequest("POST", "/api/v1/users/me/secrets", payload, &response); err != nil {
		return fmt.Errorf("failed to update Azure secrets: %w", err)
	}

	return nil
}

type AuthCookies struct {
	AuthToken     string
	EncryptionKey string
}

func (c *Client) extractAuthCookies() AuthCookies {
	var result AuthCookies

	if c.httpClient.Jar == nil {
		return result
	}

	baseURL := c.baseURL
	if baseURL == "" {
		baseURL = c.config.APIURL
	}

	parsedURL, err := parseURL(baseURL)
	if err != nil {
		return result
	}

	cookies := c.httpClient.Jar.Cookies(parsedURL)

	logger.Debug("Found %d cookies in jar", len(cookies))

	for _, cookie := range cookies {
		switch cookie.Name {
		case "access_token_cookie", "jwt", "token", "auth_token", "access_token":
			if result.AuthToken == "" {
				result.AuthToken = cookie.Value
			}
		case "enc_key":
			result.EncryptionKey = cookie.Value
		}
	}

	return result
}

func (c *Client) IsAuthenticated() bool {
	return c.config.AuthToken != ""
}

func parseURL(urlStr string) (*url.URL, error) {
	return url.Parse(urlStr)
}
