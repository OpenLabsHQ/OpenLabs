.PHONY: build clean lint

# Define the binary output name
BINARY_NAME=openlabs
VERSION=$(shell git describe --tags --always 2>/dev/null | sed 's/^v//')
BUILD_TIME=$(shell date +%FT%T%z)
LDFLAGS=-ldflags "-X github.com/OpenLabsHQ/CLI/cmd.version=$(VERSION) -X github.com/OpenLabsHQ/CLI/cmd.buildTime=$(BUILD_TIME)"

# Build for the current platform
build:
	go build -o $(BINARY_NAME) $(LDFLAGS)

# Clean the binary
clean:
	rm -f $(BINARY_NAME)
	rm -f $(BINARY_NAME)_*

# Build for all supported platforms
build-all: clean
	# Linux
	GOOS=linux GOARCH=amd64 go build -o $(BINARY_NAME)_linux_amd64 $(LDFLAGS)
	GOOS=linux GOARCH=arm64 go build -o $(BINARY_NAME)_linux_arm64 $(LDFLAGS)
	
	# macOS
	GOOS=darwin GOARCH=amd64 go build -o $(BINARY_NAME)_darwin_amd64 $(LDFLAGS)
	GOOS=darwin GOARCH=arm64 go build -o $(BINARY_NAME)_darwin_arm64 $(LDFLAGS)
	
	# Windows
	GOOS=windows GOARCH=amd64 go build -o $(BINARY_NAME)_windows_amd64.exe $(LDFLAGS)
	GOOS=windows GOARCH=arm64 go build -o $(BINARY_NAME)_windows_arm64.exe $(LDFLAGS)

# Install the binary to GOPATH/bin
install: build
	go install

# Run golangci-lint
lint:
	@which golangci-lint > /dev/null || go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	golangci-lint run ./...

# Default target
default: build
