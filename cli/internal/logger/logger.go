package logger

import (
	"log"
	"os"
)

type Level int

const (
	LevelError Level = iota
	LevelWarn
	LevelInfo
	LevelDebug
)

var (
	currentLevel = LevelInfo
	logger       = log.New(os.Stderr, "", log.LstdFlags)
)

// SetLevel sets the global logging level
func SetLevel(level Level) {
	currentLevel = level
}

// SetDebug is a convenience function to enable debug logging
func SetDebug(enabled bool) {
	if enabled {
		SetLevel(LevelDebug)
	} else {
		SetLevel(LevelInfo)
	}
}

// Debug logs a debug message
func Debug(format string, args ...interface{}) {
	if currentLevel >= LevelDebug {
		logger.Printf("[DEBUG] "+format, args...)
	}
}

// Info logs an info message
func Info(format string, args ...interface{}) {
	if currentLevel >= LevelInfo {
		logger.Printf("[INFO] "+format, args...)
	}
}

// Warn logs a warning message
func Warn(format string, args ...interface{}) {
	if currentLevel >= LevelWarn {
		logger.Printf("[WARN] "+format, args...)
	}
}

// Error logs an error message
func Error(format string, args ...interface{}) {
	if currentLevel >= LevelError {
		logger.Printf("[ERROR] "+format, args...)
	}
}

// Debugf is an alias for Debug for consistency
func Debugf(format string, args ...interface{}) {
	Debug(format, args...)
}

// Infof is an alias for Info for consistency
func Infof(format string, args ...interface{}) {
	Info(format, args...)
}

// Warnf is an alias for Warn for consistency
func Warnf(format string, args ...interface{}) {
	Warn(format, args...)
}

// Errorf is an alias for Error for consistency
func Errorf(format string, args ...interface{}) {
	Error(format, args...)
}
