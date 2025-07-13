package client

import (
	"fmt"
	"time"
)

func (c *Client) ListJobs(status string) ([]Job, error) {
	path := "/api/v1/jobs"
	if status != "" {
		path += "?job_status=" + status
	}

	var jobs []Job
	if err := c.makeRequest("GET", path, nil, &jobs); err != nil {
		return nil, fmt.Errorf("failed to list jobs: %w", err)
	}
	return jobs, nil
}

func (c *Client) GetJob(identifier string) (*Job, error) {
	var job Job
	path := fmt.Sprintf("/api/v1/jobs/%s", identifier)
	if err := c.makeRequest("GET", path, nil, &job); err != nil {
		return nil, fmt.Errorf("failed to get job %s: %w", identifier, err)
	}
	return &job, nil
}

func (c *Client) WaitForJobCompletion(jobID string, timeout time.Duration) (*Job, error) {
	deadline := time.Now().Add(timeout)
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			job, err := c.GetJob(jobID)
			if err != nil {
				return nil, err
			}

			switch job.Status {
			case "complete":
				return job, nil
			case "failed":
				errorMsg := "job failed"
				if job.ErrorMessage != "" {
					errorMsg = fmt.Sprintf("job failed: %s", job.ErrorMessage)
				}
				return job, fmt.Errorf("%s", errorMsg)
			case "queued", "in_progress":
				if time.Now().After(deadline) {
					return job, fmt.Errorf("job timeout after %v", timeout)
				}
				continue
			default:
				return job, fmt.Errorf("unknown job status: %s", job.Status)
			}

		case <-time.After(timeout):
			return nil, fmt.Errorf("job timeout after %v", timeout)
		}
	}
}

func (c *Client) IsJobComplete(jobID string) (bool, error) {
	job, err := c.GetJob(jobID)
	if err != nil {
		return false, err
	}

	return job.Status == "complete" || job.Status == "failed", nil
}

func (c *Client) GetJobStatus(jobID string) (string, error) {
	job, err := c.GetJob(jobID)
	if err != nil {
		return "", err
	}

	return job.Status, nil
}
