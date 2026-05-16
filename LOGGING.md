# NOVA Discord Bot - Logging and Error Handling Guide

## Overview

The NOVA Discord Bot now includes comprehensive logging and error handling mechanisms to make debugging easier and improve system reliability.

## Features

### 1. Structured Logging
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **File Handlers**: All logs are written to files with automatic rotation
- **Console Output**: INFO level and above appear in console
- **Error-Specific Log**: Separate file for WARNING and ERROR messages

### 2. Log Files

Logs are stored in the `logs/` directory (created automatically):

- **`logs/nova_bot.log`** - Main application log (rotates at 10 MB, keeps 5 backups)
- **`logs/nova_bot_errors.log`** - Error-only log (rotates at 5 MB, keeps 3 backups)

### 3. Automatic Log Rotation

Log files automatically rotate to prevent disk space issues:
- Main log: 10 MB per file, keeps 5 backups
- Error log: 5 MB per file, keeps 3 backups

When a log file reaches its size limit, it's renamed with a `.1`, `.2`, etc. extension, and a new log file is created.

### 4. Error Categories

Custom exception classes in `ai.py`:
- **`APIError`** - Base exception for all API-related errors
- **`ConfigError`** - Configuration or setup issues (missing API keys, files)
- **`NetworkError`** - Network-related issues (download failures)
- **`ProcessingError`** - Processing failures during response generation

## Configuration

### Setting Log Level

By default, logs are at INFO level. To change:

```bash
# Set environment variable before running
export LOG_LEVEL=DEBUG  # For verbose debugging

# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Accessing Logs

```bash
# View main log
tail -f logs/nova_bot.log

# View only errors
tail -f logs/nova_bot_errors.log

# Search for specific errors
grep "ERROR" logs/nova_bot.log

# View last 100 lines
tail -100 logs/nova_bot.log
```

## Log Output Examples

### Startup Logs
```
2024-01-15 10:30:45 - __main__ - INFO - ============================================================
2024-01-15 10:30:45 - __main__ - INFO - NOVA Discord Bot Starting
2024-01-15 10:30:45 - __main__ - INFO - ============================================================
2024-01-15 10:30:45 - __main__ - INFO - ✓ Discord token configured
2024-01-15 10:30:45 - __main__ - INFO - ✓ GenAI API key configured
2024-01-15 10:30:45 - __main__ - INFO - Starting health server on port 8080
2024-01-15 10:30:45 - __main__ - INFO - ✓ Health server listening on port 8080
2024-01-15 10:30:45 - __main__ - INFO - Starting Discord bot...
2024-01-15 10:30:46 - discord_bot - INFO - ✓ Bot connected to Discord - User: NOVA#1234
```

### Message Processing Logs (DEBUG level)
```
2024-01-15 10:31:20 - discord_bot - DEBUG - Bot mentioned in message from User123 (123456789) in MyServer
2024-01-15 10:31:20 - discord_bot - DEBUG - Processing 1 attachment(s)
2024-01-15 10:31:20 - discord_bot - DEBUG - Added image attachment: https://example.com/image.png
2024-01-15 10:31:20 - discord_bot - INFO - Responding to message from User123 with AI response
2024-01-15 10:31:22 - ai - DEBUG - Generating response for content: What is machine learning?...
2024-01-15 10:31:23 - ai - INFO - Response generated successfully
```

### Error Logs
```
2024-01-15 10:32:00 - ai - ERROR - AI API error: GENAI_API_KEY not set in environment
2024-01-15 10:32:00 - discord_bot - ERROR - AI API error: GENAI_API_KEY not set in environment, exc_info=True
2024-01-15 10:32:01 - discord_bot - INFO - AI response sent successfully
```

## Module-Specific Logging

### discord_bot.py
- Bot connection status
- Guild join/leave events
- Message processing
- Command execution
- API call errors
- Message sending failures

### ai.py
- API initialization
- Tool loading
- Image downloading and processing
- Gemini Live session events
- Response generation progress
- API errors and timeouts

### bot.py
- Startup sequence
- Environment variable validation
- Health server status
- Critical errors

### logger.py
- Logger initialization
- Log configuration confirmation

## Error Handling Patterns

### Try-Catch with Logging

All critical operations now use try-catch blocks:

```python
try:
    response = await ai.generate_response(content)
except ai.APIError as e:
    logger.error(f"AI API error: {e}", exc_info=True)
    # Handle error gracefully
```

### Graceful Error Responses

When errors occur, the bot:
1. Logs the error with full traceback (`exc_info=True`)
2. Sends a user-friendly error message to Discord
3. Continues running without crashing

## Troubleshooting

### Common Issues

#### No logs appearing
- Check that `logs/` directory exists (created automatically)
- Verify `LOG_LEVEL` environment variable is set correctly
- Check file permissions on the `logs/` directory

#### Logs growing too large
- Log rotation is automatic at 10 MB
- Old log files with `.1`, `.2`, etc. extensions are kept for history
- Manually delete old logs if needed: `rm logs/nova_bot.*.log`

#### Debugging API issues
```bash
export LOG_LEVEL=DEBUG
# Then check logs/nova_bot.log for detailed debug messages
```

## Best Practices

1. **Regular Log Review** - Check logs weekly for patterns or recurring errors
2. **Archive Old Logs** - Archive logs older than 30 days to save space
3. **Monitor Disk Space** - Ensure the `logs/` directory doesn't exceed available disk space
4. **Debug Mode** - Use `LOG_LEVEL=DEBUG` only when investigating issues, as it creates verbose output

## Performance Impact

The logging system is designed to be lightweight:
- File I/O is buffered
- Log rotation only happens at file size thresholds
- Console output is limited to INFO level and above

## Future Enhancements

Possible improvements:
- Structured logging with JSON format for parsing
- Remote logging to centralized service
- Performance metrics logging
- Metrics dashboard integration
