.PHONY: all install-deps dev dev-admin dev-student clean setup check-deps

all: install-deps

# Check prerequisites
check-deps:
	@command -v pnpm >/dev/null 2>&1 || { echo "pnpm is not installed. Please install it first: npm install -g pnpm"; exit 1; }

# Install frontend dependencies
install-deps: check-deps
	cd view && pnpm install

# Setup development environment
setup: install-deps
	@echo "Setup complete!"

# Start all portals
dev:
	cd view && pnpm dev"

# Clean build artifacts
clean:
	rm -rf bin/
