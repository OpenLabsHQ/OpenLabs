package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/url"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/config"
	"github.com/OpenLabsHQ/OpenLabs/cli/internal/logger"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
	config     *config.Config
}

type HTTPError struct {
	StatusCode int
	Message    string
	Details    interface{}
}

func (e *HTTPError) Error() string {
	if e.Details != nil {
		return fmt.Sprintf("HTTP %d: %s - %v", e.StatusCode, e.Message, e.Details)
	}
	return fmt.Sprintf("HTTP %d: %s", e.StatusCode, e.Message)
}

func New(cfg *config.Config) *Client {
	jar, err := cookiejar.New(nil)
	if err != nil {
		logger.Warn("Failed to create cookie jar: %v", err)
	}

	return &Client{
		baseURL: cfg.APIURL,
		config:  cfg,
		httpClient: &http.Client{
			Timeout: cfg.Timeout,
			Jar:     jar,
		},
	}
}

func (c *Client) makeRequest(method, path string, body interface{}, result interface{}) error {
	return c.makeRequestWithCookies(method, path, body, result, nil)
}

func (c *Client) makeRequestWithCookies(method, path string, body interface{}, result interface{}, cookieHandler func([]*http.Cookie)) error {
	requestURL := c.baseURL + path

	var reqBody io.Reader
	if body != nil {
		jsonData, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("failed to marshal request body: %w", err)
		}
		reqBody = bytes.NewReader(jsonData)
	}

	req, err := http.NewRequest(method, requestURL, reqBody)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	c.addAuthenticationHeaders(req)

	logger.Debug("Making request to %s %s", method, requestURL)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	logger.Debug("Response status: %s", resp.Status)
	logger.Debug("Response cookies: %d received", len(resp.Cookies()))

	if cookieHandler != nil {
		cookieHandler(resp.Cookies())
	}

	return c.handleResponse(resp, result)
}

func (c *Client) addAuthenticationHeaders(req *http.Request) {
	logger.Debug("Auth token available: %t", c.config.AuthToken != "")

	if c.config.AuthToken == "" {
		logger.Debug("No auth token available")
		return
	}

	parsedURL, err := url.Parse(req.URL.String())
	if err != nil {
		logger.Warn("Failed to parse URL for cookie domain: %v", err)
		return
	}

	isSecure := parsedURL.Scheme == "https"
	tokenCookie := &http.Cookie{
		Name:     "token",
		Value:    c.config.AuthToken,
		Path:     "/",
		Domain:   parsedURL.Hostname(),
		HttpOnly: true,
		Secure:   isSecure,
	}
	req.AddCookie(tokenCookie)

	logger.Debug("Added token cookie")

	if c.config.EncryptionKey != "" {
		encCookie := &http.Cookie{
			Name:     "enc_key",
			Value:    c.config.EncryptionKey,
			Path:     "/",
			Domain:   parsedURL.Hostname(),
			HttpOnly: true,
			Secure:   isSecure,
		}
		req.AddCookie(encCookie)

		logger.Debug("Added enc_key cookie")
	}
}

func (c *Client) handleResponse(resp *http.Response, result interface{}) error {
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return c.parseErrorResponse(resp.StatusCode, body)
	}

	if result != nil && len(body) > 0 {
		if err := json.Unmarshal(body, result); err != nil {
			return fmt.Errorf("failed to parse response: %w", err)
		}
	}

	return nil
}

func (c *Client) parseErrorResponse(statusCode int, body []byte) error {
	var errorData map[string]interface{}

	if len(body) > 0 && json.Unmarshal(body, &errorData) == nil {
		if detail, ok := errorData["detail"]; ok {
			return &HTTPError{
				StatusCode: statusCode,
				Message:    http.StatusText(statusCode),
				Details:    detail,
			}
		}
	}

	return &HTTPError{
		StatusCode: statusCode,
		Message:    http.StatusText(statusCode),
	}
}

func (c *Client) Ping() error {
	return c.makeRequest("GET", "/api/v1/health/ping", nil, nil)
}
