package progress

import (
	"fmt"
	"time"
)

type Spinner struct {
	message   string
	chars     []rune
	index     int
	done      chan bool
	isRunning bool
}

func NewSpinner(message string) *Spinner {
	return &Spinner{
		message: message,
		chars:   []rune{'⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'},
		done:    make(chan bool),
	}
}

func (s *Spinner) Start() {
	if s.isRunning {
		return
	}

	s.isRunning = true
	go s.spin()
}

func (s *Spinner) Stop() {
	if !s.isRunning {
		return
	}

	s.isRunning = false
	s.done <- true
	fmt.Print("\r\033[K")
}

func (s *Spinner) UpdateMessage(message string) {
	s.message = message
}

func (s *Spinner) spin() {
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-s.done:
			return
		case <-ticker.C:
			fmt.Printf("\r%c %s", s.chars[s.index], s.message)
			s.index = (s.index + 1) % len(s.chars)
		}
	}
}

func ShowSuccess(message string) {
	fmt.Printf("✓ %s\n", message)
}

func ShowError(message string) {
	fmt.Printf("✗ %s\n", message)
}

func ShowInfo(message string) {
	fmt.Printf("%s\n", message)
}

func ShowWarning(message string) {
	fmt.Printf("⚠ %s\n", message)
}
