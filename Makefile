# Honda Veteran Talent Matching System - Makefile

.PHONY: help install install-dev test test-unit test-integration lint format type-check security-check clean deploy deploy-dev deploy-prod remove logs

# Default target
help:
	@echo "Honda Veteran Talent Matching System"
	@echo ""
	@echo "Available commands:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-check   Run security checks with bandit"
	@echo "  clean            Clean up build artifacts"
	@echo "  deploy           Deploy to development environment"
	@echo "  deploy-dev       Deploy to development environment"
	@echo "  deploy-prod      Deploy to production environment"
	@echo "  remove           Remove deployed stack"
	@echo "  logs             Show logs for a function (usage: make logs FUNC=functionName)"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	npm install
	cd frontend && npm install
	pre-commit install

# Testing
test: test-unit test-integration

test-unit:
	pytest tests/unit/ -v --cov=src --cov-report=term-missing --cov-report=html

test-integration:
	pytest tests/integration/ -v

# Code quality
lint:
	flake8 src/ tests/
	cd frontend && npm run lint

format:
	black src/ tests/
	isort src/ tests/
	cd frontend && npm run lint:fix

type-check:
	mypy src/

security-check:
	bandit -r src/
	safety check

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	cd frontend && rm -rf build/ node_modules/.cache/

# Deployment
deploy: deploy-dev

deploy-dev:
	serverless deploy --stage dev

deploy-prod:
	serverless deploy --stage prod

remove:
	serverless remove

# Monitoring
logs:
	serverless logs -f $(FUNC) --tail

# Frontend specific commands
frontend-install:
	cd frontend && npm install

frontend-start:
	cd frontend && npm start

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make deploy-dev' to deploy to AWS"
	@echo "Run 'make frontend-start' to start the frontend development server"

# CI/CD simulation
ci-check: format lint type-check security-check test
	@echo "All CI checks passed!"