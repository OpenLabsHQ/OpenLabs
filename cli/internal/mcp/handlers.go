package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/OpenLabsHQ/OpenLabs/cli/internal/client"
)

func (s *Server) checkAuthAndReturnError() *mcp.CallToolResult {
	if !s.client.IsAuthenticated() {
		if s.reloadConfigIfChanged() {
			if s.client.IsAuthenticated() {
				return nil
			}
		}
		
		return mcp.NewToolResultError("Not authenticated. Please use 'openlabs auth login' or use the login tool with your email and password to authenticate.")
	}
	return nil
}

func (s *Server) handleListRanges(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	ranges, err := s.client.ListRanges()
	if err != nil {
		return mcp.NewToolResultError("Failed to list ranges: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(ranges, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Found %d deployed ranges:\n\n%s", len(ranges), string(data))), nil
}

func (s *Server) handleGetRangeDetails(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	rangeID, err := requireInt(request, "range_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid range_id parameter"), nil
	}

	details, err := s.client.GetRange(rangeID)
	if err != nil {
		return mcp.NewToolResultError("Failed to get range details: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(details, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Range %d details:\n\n%s", rangeID, string(data))), nil
}

func (s *Server) handleGetRangeKey(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	rangeID, err := requireInt(request, "range_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid range_id parameter"), nil
	}

	keyResponse, err := s.client.GetRangeKey(rangeID)
	if err != nil {
		return mcp.NewToolResultError("Failed to get range key: " + err.Error()), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("SSH private key for range %d:\n\n%s", rangeID, keyResponse.RangePrivateKey)), nil
}

func (s *Server) handleListBlueprints(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	blueprints, err := s.client.ListBlueprintRanges()
	if err != nil {
		return mcp.NewToolResultError("Failed to list blueprints: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(blueprints, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Found %d available blueprints:\n\n%s", len(blueprints), string(data))), nil
}

func (s *Server) handleGetBlueprintDetails(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	blueprintID, err := requireInt(request, "blueprint_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid blueprint_id parameter"), nil
	}

	details, err := s.client.GetBlueprintRange(blueprintID)
	if err != nil {
		return mcp.NewToolResultError("Failed to get blueprint details: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(details, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Blueprint %d details:\n\n%s", blueprintID, string(data))), nil
}

func (s *Server) handleCheckJobStatus(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	jobID, err := requireString(request, "job_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid job_id parameter"), nil
	}

	status, err := s.client.GetJob(jobID)
	if err != nil {
		return mcp.NewToolResultError("Failed to check job status: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Job %s status:\n\n%s", jobID, string(data))), nil
}

func (s *Server) handleGetUserInfo(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	userInfo, err := s.client.GetUserInfo()
	if err != nil {
		return mcp.NewToolResultError("Failed to get user info: " + err.Error()), nil
	}

	isAdmin := userInfo.Admin

	adminStatus := "Standard User"
	capabilities := "Can list/deploy ranges, manage own resources and credentials"
	if isAdmin {
		adminStatus = "Administrator" 
		capabilities = "Full platform access including blueprint creation/deletion"
	}

	data, err := json.MarshalIndent(userInfo, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf(`Current user information:

%s

Role: %s
Capabilities: %s

Authentication status: Authenticated and ready for OpenLabs operations`, 
		string(data), adminStatus, capabilities)), nil
}

func (s *Server) handleDeployRange(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	name, err := requireString(request, "name")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid name parameter"), nil
	}

	blueprintID, err := requireInt(request, "blueprint_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid blueprint_id parameter"), nil
	}

	region, err := requireString(request, "region")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid region parameter"), nil
	}

	description := getStringOptional(request, "description")

	deployRequest := &client.DeployRangeRequest{
		Name:        name,
		BlueprintID: blueprintID,
		Region:      region,
		Description: description,
	}

	result, err := s.client.DeployRange(deployRequest)
	if err != nil {
		return mcp.NewToolResultError("Failed to deploy range: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Successfully deployed range '%s':\n\n%s", name, string(data))), nil
}

func (s *Server) handleDestroyRange(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	rangeID, err := requireInt(request, "range_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid range_id parameter"), nil
	}

	confirm, err := requireBool(request, "confirm")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid confirm parameter - must be true to confirm destruction"), nil
	}

	if !confirm {
		return mcp.NewToolResultError("Destruction not confirmed - confirm parameter must be true"), nil
	}

	result, err := s.client.DeleteRange(rangeID)
	if err != nil {
		return mcp.NewToolResultError("Failed to destroy range: " + err.Error()), nil
	}

	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Successfully initiated destruction of range %d:\n\n%s", rangeID, string(data))), nil
}

func (s *Server) handleCreateBlueprint(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	args := request.GetArguments()
	blueprintData, ok := args["blueprint"]
	if !ok {
		return mcp.NewToolResultError("Missing blueprint parameter"), nil
	}

	data, err := json.Marshal(blueprintData)
	if err != nil {
		return mcp.NewToolResultError("Invalid blueprint data format"), nil
	}

	var blueprint map[string]interface{}
	if err := json.Unmarshal(data, &blueprint); err != nil {
		return mcp.NewToolResultError("Invalid blueprint JSON format"), nil
	}

	result, err := s.client.CreateBlueprintRange(blueprint)
	if err != nil {
		return mcp.NewToolResultError("Failed to create blueprint: " + err.Error()), nil
	}

	resultData, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return mcp.NewToolResultError("Failed to format response"), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Successfully created blueprint:\n\n%s", string(resultData))), nil
}

func (s *Server) handleDeleteBlueprint(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	blueprintID, err := requireInt(request, "blueprint_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid blueprint_id parameter"), nil
	}

	confirm, err := requireBool(request, "confirm")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid confirm parameter - must be true to confirm deletion"), nil
	}

	if !confirm {
		return mcp.NewToolResultError("Deletion not confirmed - confirm parameter must be true"), nil
	}

	err = s.client.DeleteBlueprintRange(blueprintID)
	if err != nil {
		return mcp.NewToolResultError("Failed to delete blueprint: " + err.Error()), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Successfully deleted blueprint %d", blueprintID)), nil
}

func (s *Server) handleUpdateAWSSecrets(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	accessKey, err := requireString(request, "aws_access_key")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid aws_access_key parameter"), nil
	}

	secretKey, err := requireString(request, "aws_secret_key")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid aws_secret_key parameter"), nil
	}

	err = s.client.UpdateAWSSecrets(accessKey, secretKey)
	if err != nil {
		return mcp.NewToolResultError("Failed to update AWS secrets: " + err.Error()), nil
	}

	return mcp.NewToolResultText("Successfully updated AWS credentials"), nil
}

func (s *Server) handleUpdateAzureSecrets(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if authErr := s.checkAuthAndReturnError(); authErr != nil {
		return authErr, nil
	}
	clientID, err := requireString(request, "azure_client_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid azure_client_id parameter"), nil
	}

	clientSecret, err := requireString(request, "azure_client_secret")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid azure_client_secret parameter"), nil
	}

	tenantID, err := requireString(request, "azure_tenant_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid azure_tenant_id parameter"), nil
	}

	subscriptionID, err := requireString(request, "azure_subscription_id")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid azure_subscription_id parameter"), nil
	}

	err = s.client.UpdateAzureSecrets(clientID, clientSecret, tenantID, subscriptionID)
	if err != nil {
		return mcp.NewToolResultError("Failed to update Azure secrets: " + err.Error()), nil
	}

	return mcp.NewToolResultText("Successfully updated Azure credentials"), nil
}

func (s *Server) handleLogin(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	email, err := requireString(request, "email")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid email parameter"), nil
	}

	password, err := requireString(request, "password")
	if err != nil {
		return mcp.NewToolResultError("Missing or invalid password parameter"), nil
	}

	err = s.client.Login(email, password)
	if err != nil {
		return mcp.NewToolResultError("Login failed: " + err.Error()), nil
	}

	userInfo, err := s.client.GetUserInfo()
	if err != nil {
		return mcp.NewToolResultText("Successfully logged in to OpenLabs, but failed to get user details"), nil
	}

	isAdmin := userInfo.Admin

	adminStatus := "Standard User"
	capabilities := "You can list/deploy ranges, manage your own resources and credentials"
	if isAdmin {
		adminStatus = "Administrator"
		capabilities = "You have full platform access including blueprint creation/deletion"
	}

	return mcp.NewToolResultText(fmt.Sprintf(`Successfully logged in to OpenLabs!

User Details:
- Name: %s
- Email: %s  
- Role: %s

%s

All OpenLabs MCP tools are now available for use. The authentication state is now updated for this session.`, 
		userInfo.Name, userInfo.Email, adminStatus, capabilities)), nil
}

func requireString(request mcp.CallToolRequest, key string) (string, error) {
	args := request.GetArguments()
	value, ok := args[key]
	if !ok {
		return "", fmt.Errorf("missing parameter: %s", key)
	}

	if str, ok := value.(string); ok {
		return str, nil
	}
	return "", fmt.Errorf("parameter %s is not a string", key)
}

func requireInt(request mcp.CallToolRequest, key string) (int, error) {
	args := request.GetArguments()
	value, ok := args[key]
	if !ok {
		return 0, fmt.Errorf("missing parameter: %s", key)
	}

	switch v := value.(type) {
	case int:
		return v, nil
	case float64:
		return int(v), nil
	case string:
		return strconv.Atoi(v)
	default:
		return 0, fmt.Errorf("parameter %s is not an integer", key)
	}
}

func requireBool(request mcp.CallToolRequest, key string) (bool, error) {
	args := request.GetArguments()
	value, ok := args[key]
	if !ok {
		return false, fmt.Errorf("missing parameter: %s", key)
	}

	switch v := value.(type) {
	case bool:
		return v, nil
	case string:
		return strconv.ParseBool(v)
	default:
		return false, fmt.Errorf("parameter %s is not a boolean", key)
	}
}

func getStringOptional(request mcp.CallToolRequest, key string) string {
	args := request.GetArguments()
	value, ok := args[key]
	if !ok {
		return ""
	}

	if str, ok := value.(string); ok {
		return str
	}
	return ""
}