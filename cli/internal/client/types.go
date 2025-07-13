package client

import "time"

type UserCredentials struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type UserRegistration struct {
	Name     string `json:"name"`
	Email    string `json:"email"`
	Password string `json:"password"`
}

type LoginResponse struct {
	Success bool `json:"success"`
}

type UserInfo struct {
	Name  string `json:"name"`
	Email string `json:"email"`
	Admin bool   `json:"admin"`
}

type PasswordUpdate struct {
	CurrentPassword string `json:"current_password"`
	NewPassword     string `json:"new_password"`
}

type AWSSecrets struct {
	AccessKey string `json:"aws_access_key"`
	SecretKey string `json:"aws_secret_key"`
}

type AzureSecrets struct {
	ClientID       string `json:"azure_client_id"`
	ClientSecret   string `json:"azure_client_secret"`
	TenantID       string `json:"azure_tenant_id"`
	SubscriptionID string `json:"azure_subscription_id"`
}

type CloudSecretStatus struct {
	HasCredentials bool       `json:"has_credentials"`
	CreatedAt      *time.Time `json:"created_at,omitempty"`
}

type UserSecretResponse struct {
	AWS   CloudSecretStatus `json:"aws"`
	Azure CloudSecretStatus `json:"azure"`
}

type BlueprintRangeHeader struct {
	ID          int    `json:"id"`
	Provider    string `json:"provider"`
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	VNC         bool   `json:"vnc"`
	VPN         bool   `json:"vpn"`
}

type BlueprintRange struct {
	BlueprintRangeHeader
	VPCs []BlueprintVPC `json:"vpcs"`
}

type BlueprintVPCHeader struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
	CIDR string `json:"cidr"`
}

type BlueprintVPC struct {
	BlueprintVPCHeader
	Subnets []BlueprintSubnet `json:"subnets"`
}

type BlueprintSubnetHeader struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
	CIDR string `json:"cidr"`
}

type BlueprintSubnet struct {
	BlueprintSubnetHeader
	Hosts []BlueprintHost `json:"hosts"`
}

type BlueprintHostHeader struct {
	ID       int      `json:"id"`
	Hostname string   `json:"hostname"`
	OS       string   `json:"os"`
	Spec     string   `json:"spec"`
	Size     int      `json:"size"`
	Tags     []string `json:"tags,omitempty"`
}

type BlueprintHost struct {
	BlueprintHostHeader
}

type DeployedRangeHeader struct {
	ID          int       `json:"id"`
	Provider    string    `json:"provider"`
	Name        string    `json:"name"`
	Description string    `json:"description,omitempty"`
	Date        time.Time `json:"date"`
	State       string    `json:"state"`
	Region      string    `json:"region"`
	VNC         bool      `json:"vnc"`
	VPN         bool      `json:"vpn"`
}

type DeployedRange struct {
	DeployedRangeHeader
	JumpboxResourceID string        `json:"jumpbox_resource_id"`
	JumpboxPublicIP   string        `json:"jumpbox_public_ip"`
	RangePrivateKey   string        `json:"range_private_key"`
	StateFile         interface{}   `json:"state_file"`
	Readme            string        `json:"readme,omitempty"`
	VPCs              []DeployedVPC `json:"vpcs"`
}

type DeployedVPC struct {
	ID         int              `json:"id"`
	Name       string           `json:"name"`
	CIDR       string           `json:"cidr"`
	ResourceID string           `json:"resource_id"`
	Subnets    []DeployedSubnet `json:"subnets"`
}

type DeployedSubnet struct {
	ID         int            `json:"id"`
	Name       string         `json:"name"`
	CIDR       string         `json:"cidr"`
	ResourceID string         `json:"resource_id"`
	Hosts      []DeployedHost `json:"hosts"`
}

type DeployedHost struct {
	ID         int      `json:"id"`
	Hostname   string   `json:"hostname"`
	OS         string   `json:"os"`
	Spec       string   `json:"spec"`
	Size       int      `json:"size"`
	Tags       []string `json:"tags,omitempty"`
	ResourceID string   `json:"resource_id"`
	IPAddress  string   `json:"ip_address"`
}

type DeployRangeRequest struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	BlueprintID int    `json:"blueprint_id"`
	Region      string `json:"region"`
}

type Job struct {
	ID           int         `json:"id"`
	ARQJobID     string      `json:"arq_job_id"`
	JobName      string      `json:"job_name"`
	JobTry       *int        `json:"job_try,omitempty"`
	EnqueueTime  time.Time   `json:"enqueue_time"`
	StartTime    *time.Time  `json:"start_time,omitempty"`
	FinishTime   *time.Time  `json:"finish_time,omitempty"`
	Status       string      `json:"status"`
	Result       interface{} `json:"result,omitempty"`
	ErrorMessage string      `json:"error_message,omitempty"`
}

type JobSubmissionResponse struct {
	ARQJobID string `json:"arq_job_id"`
	Detail   string `json:"detail"`
}

type RangeKeyResponse struct {
	RangePrivateKey string `json:"range_private_key"`
}

type Message struct {
	Message string `json:"message"`
}
