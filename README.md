# DUQ Safety Service

Standalone safety evaluation microservice for DUQ multi-agent system.

## Features

- Rule-based safety checks (keywords, patterns)
- LLM-based safety evaluation (GPT-4o via OpenRouter)
- Telegram alerting for flagged requests
- Redis pub/sub for safety events

## Ports

- 8083: HTTP API

## API Endpoints

- `POST /check` - Evaluate request safety
- `GET /health` - Health check

## Environment Variables

- `ANTHROPIC_API_KEY` - Anthropic API key (optional)
- `OPENROUTER_API_KEY` - OpenRouter API key (required)
- `TELEGRAM_BOT_TOKEN` - Telegram bot token for alerts
- `TELEGRAM_ALERT_CHAT_ID` - Chat ID for alerts
