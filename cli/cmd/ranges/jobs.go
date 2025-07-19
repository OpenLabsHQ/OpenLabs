package ranges

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"

	"github.com/OpenLabsHQ/CLI/internal/output"
	"github.com/OpenLabsHQ/CLI/internal/utils"
)

func newJobsCommand() *cobra.Command {
	var status string

	cmd := &cobra.Command{
		Use:   "jobs",
		Short: "List range deployment jobs",
		Long:  "Display a table of range deployment and destruction jobs with their status.",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runJobs(status)
		},
	}

	cmd.Flags().StringVarP(&status, "status", "s", "", "filter by job status (queued, in_progress, complete, failed)")

	return cmd
}

func runJobs(status string) error {
	apiClient := getClient()

	if !apiClient.IsAuthenticated() {
		return fmt.Errorf("not authenticated. Run 'openlabs auth login' first")
	}

	jobs, err := apiClient.ListJobs(status)
	if err != nil {
		// Handle 404 responses that indicate no jobs found
		if strings.Contains(err.Error(), "HTTP 404") && strings.Contains(err.Error(), "jobs that you own") {
			fmt.Println("No jobs found.")
			return nil
		}
		return fmt.Errorf("failed to list jobs: %w", err)
	}

	// Filter to only range-related jobs
	var rangeJobs []JobDisplay
	for _, job := range jobs {
		if isRangeJob(job.JobName) {
			display := JobDisplay{
				ID:          job.ARQJobID,
				Type:        getJobType(job.JobName),
				Status:      job.Status,
				EnqueueTime: job.EnqueueTime.Format("2006-01-02 15:04:05"),
				RangeName:   extractRangeName(job.Result),
			}

			if job.StartTime != nil {
				display.StartTime = job.StartTime.Format("15:04:05")
			}

			if job.FinishTime != nil {
				display.FinishTime = job.FinishTime.Format("15:04:05")
			}

			if job.Status == "failed" && job.ErrorMessage != "" {
				display.Error = utils.TruncateString(job.ErrorMessage, 50)
			}

			rangeJobs = append(rangeJobs, display)
		}
	}

	if len(rangeJobs) == 0 {
		fmt.Println("No range jobs found.")
		return nil
	}

	return output.Display(rangeJobs, globalConfig.OutputFormat)
}

type JobDisplay struct {
	ID          string `json:"id" table:"JOB ID"`
	Type        string `json:"type" table:"TYPE"`
	RangeName   string `json:"range_name" table:"RANGE"`
	Status      string `json:"status" table:"STATUS"`
	EnqueueTime string `json:"enqueue_time" table:"QUEUED"`
	StartTime   string `json:"start_time,omitempty" table:"STARTED"`
	FinishTime  string `json:"finish_time,omitempty" table:"FINISHED"`
	Error       string `json:"error,omitempty" table:"ERROR"`
}

func isRangeJob(jobName string) bool {
	rangeJobTypes := []string{
		"deploy_range",
		"delete_range",
		"destroy_range",
	}

	for _, jobType := range rangeJobTypes {
		if strings.Contains(strings.ToLower(jobName), jobType) {
			return true
		}
	}

	return false
}

func getJobType(jobName string) string {
	jobName = strings.ToLower(jobName)

	if strings.Contains(jobName, "deploy") {
		return "Deploy"
	}
	if strings.Contains(jobName, "delete") || strings.Contains(jobName, "destroy") {
		return "Destroy"
	}

	return "Range"
}


func extractRangeName(result interface{}) string {
	if result == nil {
		return ""
	}

	// Try to extract name from result map
	if resultMap, ok := result.(map[string]interface{}); ok {
		if name, exists := resultMap["name"]; exists {
			if nameStr, ok := name.(string); ok {
				return nameStr
			}
		}
	}

	return ""
}
