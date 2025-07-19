package client

import "fmt"

func (c *Client) ListBlueprintRanges() ([]BlueprintRangeHeader, error) {
	var blueprints []BlueprintRangeHeader
	if err := c.makeRequest("GET", "/api/v1/blueprints/ranges", nil, &blueprints); err != nil {
		if httpErr, ok := err.(*HTTPError); ok && httpErr.StatusCode == 404 {
			return []BlueprintRangeHeader{}, nil
		}
		return nil, fmt.Errorf("failed to list blueprint ranges: %w", err)
	}
	return blueprints, nil
}

func (c *Client) GetBlueprintRange(id int) (*BlueprintRange, error) {
	var blueprint BlueprintRange
	path := fmt.Sprintf("/api/v1/blueprints/ranges/%d", id)
	if err := c.makeRequest("GET", path, nil, &blueprint); err != nil {
		return nil, fmt.Errorf("failed to get blueprint range %d: %w", id, err)
	}
	return &blueprint, nil
}

func (c *Client) CreateBlueprintRange(blueprint interface{}) (*BlueprintRangeHeader, error) {
	var result BlueprintRangeHeader
	if err := c.makeRequest("POST", "/api/v1/blueprints/ranges", blueprint, &result); err != nil {
		return nil, fmt.Errorf("failed to create blueprint range: %w", err)
	}
	return &result, nil
}

func (c *Client) DeleteBlueprintRange(id int) error {
	path := fmt.Sprintf("/api/v1/blueprints/ranges/%d", id)
	if err := c.makeRequest("DELETE", path, nil, nil); err != nil {
		return fmt.Errorf("failed to delete blueprint range %d: %w", id, err)
	}
	return nil
}

func (c *Client) ListBlueprintVPCs(standaloneOnly bool) ([]BlueprintVPCHeader, error) {
	path := "/api/v1/blueprints/vpcs"
	if !standaloneOnly {
		path += "?standalone_only=false"
	}

	var vpcs []BlueprintVPCHeader
	if err := c.makeRequest("GET", path, nil, &vpcs); err != nil {
		return nil, fmt.Errorf("failed to list blueprint VPCs: %w", err)
	}
	return vpcs, nil
}

func (c *Client) GetBlueprintVPC(id int) (*BlueprintVPC, error) {
	var vpc BlueprintVPC
	path := fmt.Sprintf("/api/v1/blueprints/vpcs/%d", id)
	if err := c.makeRequest("GET", path, nil, &vpc); err != nil {
		return nil, fmt.Errorf("failed to get blueprint VPC %d: %w", id, err)
	}
	return &vpc, nil
}

func (c *Client) CreateBlueprintVPC(vpc interface{}) (*BlueprintVPCHeader, error) {
	var result BlueprintVPCHeader
	if err := c.makeRequest("POST", "/api/v1/blueprints/vpcs", vpc, &result); err != nil {
		return nil, fmt.Errorf("failed to create blueprint VPC: %w", err)
	}
	return &result, nil
}

func (c *Client) DeleteBlueprintVPC(id int) error {
	path := fmt.Sprintf("/api/v1/blueprints/vpcs/%d", id)
	if err := c.makeRequest("DELETE", path, nil, nil); err != nil {
		return fmt.Errorf("failed to delete blueprint VPC %d: %w", id, err)
	}
	return nil
}

func (c *Client) ListBlueprintSubnets(standaloneOnly bool) ([]BlueprintSubnetHeader, error) {
	path := "/api/v1/blueprints/subnets"
	if !standaloneOnly {
		path += "?standalone_only=false"
	}

	var subnets []BlueprintSubnetHeader
	if err := c.makeRequest("GET", path, nil, &subnets); err != nil {
		return nil, fmt.Errorf("failed to list blueprint subnets: %w", err)
	}
	return subnets, nil
}

func (c *Client) GetBlueprintSubnet(id int) (*BlueprintSubnet, error) {
	var subnet BlueprintSubnet
	path := fmt.Sprintf("/api/v1/blueprints/subnets/%d", id)
	if err := c.makeRequest("GET", path, nil, &subnet); err != nil {
		return nil, fmt.Errorf("failed to get blueprint subnet %d: %w", id, err)
	}
	return &subnet, nil
}

func (c *Client) CreateBlueprintSubnet(subnet interface{}) (*BlueprintSubnetHeader, error) {
	var result BlueprintSubnetHeader
	if err := c.makeRequest("POST", "/api/v1/blueprints/subnets", subnet, &result); err != nil {
		return nil, fmt.Errorf("failed to create blueprint subnet: %w", err)
	}
	return &result, nil
}

func (c *Client) DeleteBlueprintSubnet(id int) error {
	path := fmt.Sprintf("/api/v1/blueprints/subnets/%d", id)
	if err := c.makeRequest("DELETE", path, nil, nil); err != nil {
		return fmt.Errorf("failed to delete blueprint subnet %d: %w", id, err)
	}
	return nil
}

func (c *Client) ListBlueprintHosts(standaloneOnly bool) ([]BlueprintHostHeader, error) {
	path := "/api/v1/blueprints/hosts"
	if !standaloneOnly {
		path += "?standalone_only=false"
	}

	var hosts []BlueprintHostHeader
	if err := c.makeRequest("GET", path, nil, &hosts); err != nil {
		return nil, fmt.Errorf("failed to list blueprint hosts: %w", err)
	}
	return hosts, nil
}

func (c *Client) GetBlueprintHost(id int) (*BlueprintHost, error) {
	var host BlueprintHost
	path := fmt.Sprintf("/api/v1/blueprints/hosts/%d", id)
	if err := c.makeRequest("GET", path, nil, &host); err != nil {
		return nil, fmt.Errorf("failed to get blueprint host %d: %w", id, err)
	}
	return &host, nil
}

func (c *Client) CreateBlueprintHost(host interface{}) (*BlueprintHostHeader, error) {
	var result BlueprintHostHeader
	if err := c.makeRequest("POST", "/api/v1/blueprints/hosts", host, &result); err != nil {
		return nil, fmt.Errorf("failed to create blueprint host: %w", err)
	}
	return &result, nil
}

func (c *Client) DeleteBlueprintHost(id int) error {
	path := fmt.Sprintf("/api/v1/blueprints/hosts/%d", id)
	if err := c.makeRequest("DELETE", path, nil, nil); err != nil {
		return fmt.Errorf("failed to delete blueprint host %d: %w", id, err)
	}
	return nil
}
