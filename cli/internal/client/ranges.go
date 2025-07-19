package client

import "fmt"

func (c *Client) ListRanges() ([]DeployedRangeHeader, error) {
	var ranges []DeployedRangeHeader
	if err := c.makeRequest("GET", "/api/v1/ranges", nil, &ranges); err != nil {
		if httpErr, ok := err.(*HTTPError); ok && httpErr.StatusCode == 404 {
			return []DeployedRangeHeader{}, nil
		}
		return nil, fmt.Errorf("failed to list ranges: %w", err)
	}
	return ranges, nil
}

func (c *Client) GetRange(id int) (*DeployedRange, error) {
	var rangeData DeployedRange
	path := fmt.Sprintf("/api/v1/ranges/%d", id)
	if err := c.makeRequest("GET", path, nil, &rangeData); err != nil {
		return nil, fmt.Errorf("failed to get range %d: %w", id, err)
	}
	return &rangeData, nil
}

func (c *Client) DeployRange(request *DeployRangeRequest) (*JobSubmissionResponse, error) {
	var response JobSubmissionResponse
	if err := c.makeRequest("POST", "/api/v1/ranges/deploy", request, &response); err != nil {
		return nil, fmt.Errorf("failed to deploy range: %w", err)
	}
	return &response, nil
}

func (c *Client) DeleteRange(id int) (*JobSubmissionResponse, error) {
	var response JobSubmissionResponse
	path := fmt.Sprintf("/api/v1/ranges/%d", id)
	if err := c.makeRequest("DELETE", path, nil, &response); err != nil {
		return nil, fmt.Errorf("failed to delete range %d: %w", id, err)
	}
	return &response, nil
}

func (c *Client) GetRangeKey(id int) (*RangeKeyResponse, error) {
	var keyResponse RangeKeyResponse
	path := fmt.Sprintf("/api/v1/ranges/%d/key", id)
	if err := c.makeRequest("GET", path, nil, &keyResponse); err != nil {
		return nil, fmt.Errorf("failed to get range key for %d: %w", id, err)
	}
	return &keyResponse, nil
}
