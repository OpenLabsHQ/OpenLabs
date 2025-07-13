package progress

import (
	"fmt"
	"time"

	"github.com/OpenLabsHQ/CLI/internal/client"
)

type JobTracker struct {
	client  *client.Client
	spinner *Spinner
}

func NewJobTracker(c *client.Client) *JobTracker {
	return &JobTracker{
		client: c,
	}
}

func (jt *JobTracker) TrackJob(jobID, initialMessage string, timeout time.Duration) (*client.Job, error) {
	jt.spinner = NewSpinner(initialMessage)
	jt.spinner.Start()
	defer jt.spinner.Stop()

	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	timer := time.NewTimer(timeout)
	defer timer.Stop()

	lastStatus := ""

	for {
		select {
		case <-ticker.C:
			job, err := jt.client.GetJob(jobID)
			if err != nil {
				return nil, fmt.Errorf("failed to check job status: %w", err)
			}

			if job.Status != lastStatus {
				jt.updateSpinnerMessage(job)
				lastStatus = job.Status
			}

			switch job.Status {
			case "complete":
				jt.spinner.Stop()
				ShowSuccess(fmt.Sprintf("Job completed successfully (ID: %s)", jobID))
				return job, nil

			case "failed":
				jt.spinner.Stop()
				errorMsg := "Job failed"
				if job.ErrorMessage != "" {
					errorMsg = fmt.Sprintf("Job failed: %s", job.ErrorMessage)
				}
				ShowError(fmt.Sprintf("%s (ID: %s)", errorMsg, jobID))
				return job, fmt.Errorf("%s", errorMsg)

			case "queued":
				continue

			case "in_progress":
				continue

			default:
				jt.spinner.Stop()
				ShowError(fmt.Sprintf("Unknown job status: %s (ID: %s)", job.Status, jobID))
				return job, fmt.Errorf("unknown job status: %s", job.Status)
			}

		case <-timer.C:
			jt.spinner.Stop()
			ShowError(fmt.Sprintf("Job timeout after %v (ID: %s)", timeout, jobID))
			return nil, fmt.Errorf("job timeout after %v", timeout)
		}
	}
}

func (jt *JobTracker) updateSpinnerMessage(job *client.Job) {
	var message string

	switch job.Status {
	case "queued":
		message = fmt.Sprintf("Job queued (ID: %s)", job.ARQJobID)
	case "in_progress":
		message = fmt.Sprintf("Job in progress (ID: %s)", job.ARQJobID)
		if job.StartTime != nil {
			elapsed := time.Since(*job.StartTime)
			message = fmt.Sprintf("Job running for %v (ID: %s)", elapsed.Round(time.Second), job.ARQJobID)
		}
	case "complete":
		message = fmt.Sprintf("Job completed (ID: %s)", job.ARQJobID)
	case "failed":
		message = fmt.Sprintf("Job failed (ID: %s)", job.ARQJobID)
	default:
		message = fmt.Sprintf("Job status: %s (ID: %s)", job.Status, job.ARQJobID)
	}

	jt.spinner.UpdateMessage(message)
}
