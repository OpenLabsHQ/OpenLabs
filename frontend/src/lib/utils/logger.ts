/**
 * Simple logging utility that provides structured logging
 * with different log levels and context information
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

interface LogEntry {
  level: LogLevel
  message: string
  context?: string
  data?: unknown
  timestamp: Date
}

class Logger {
  private level: LogLevel = LogLevel.INFO

  constructor(level: LogLevel = LogLevel.INFO) {
    this.level = level
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.level
  }

  private formatMessage(entry: LogEntry): string {
    const timestamp = entry.timestamp.toISOString()
    const levelName = LogLevel[entry.level]
    const context = entry.context ? `[${entry.context}]` : ''
    return `${timestamp} ${levelName} ${context} ${entry.message}`
  }

  private log(level: LogLevel, message: string, context?: string, data?: unknown) {
    if (!this.shouldLog(level)) return

    const entry: LogEntry = {
      level,
      message,
      context,
      data,
      timestamp: new Date()
    }

    const formattedMessage = this.formatMessage(entry)

    // Use appropriate console method based on log level
    switch (level) {
      case LogLevel.DEBUG:
        console.debug(formattedMessage, data)
        break
      case LogLevel.INFO:
        console.info(formattedMessage, data)
        break
      case LogLevel.WARN:
        console.warn(formattedMessage, data)
        break
      case LogLevel.ERROR:
        console.error(formattedMessage, data)
        break
    }
  }

  debug(message: string, context?: string, data?: unknown) {
    this.log(LogLevel.DEBUG, message, context, data)
  }

  info(message: string, context?: string, data?: unknown) {
    this.log(LogLevel.INFO, message, context, data)
  }

  warn(message: string, context?: string, data?: unknown) {
    this.log(LogLevel.WARN, message, context, data)
  }

  error(message: string, context?: string, data?: unknown) {
    this.log(LogLevel.ERROR, message, context, data)
  }

  setLevel(level: LogLevel) {
    this.level = level
  }
}

// Create default logger instance
const logger = new Logger(
  // Set log level based on environment
  typeof window !== 'undefined' && window.location?.hostname === 'localhost'
    ? LogLevel.DEBUG
    : LogLevel.INFO
)

export { logger }
export default logger