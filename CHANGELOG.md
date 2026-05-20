# Changelog

All notable changes to this project will be documented in this file.

## [4.1.0] - 2026-05-08

### Added
- CDN-based model downloads with SHA256 verification
- Pattern recognition models for pump/dump detection
- Whale tracker model for large wallet monitoring
- Rug pull detector model for scam token identification
- Automatic model versioning and caching
- Heuristic fallback mode when CDN unavailable

### Changed
- Refactored prediction engine for model-based scoring
- Improved risk analyzer with honeypot checks
- Enhanced mempool monitoring with WebSocket reconnection

## [3.0.0] - 2026-02-14

### Added
- Continuous monitoring mode with pair scanner
- Real-time Telegram alert bot
- Web dashboard with live predictions
- Rich CLI interface with formatted tables
- Fibonacci-based price target calculation
- Sandwich attack detection in mempool

### Changed
- Breaking: Configuration restructured for pydantic-settings
- Migrated from Web3.py v5 to v6

## [1.0.0] - 2025-12-01

### Added
- Initial release
- BSC PancakeSwap pair scanning
- Contract risk assessment (ownership, LP lock, honeypot)
- Basic prediction heuristics
- Backtest command for historical pairs
