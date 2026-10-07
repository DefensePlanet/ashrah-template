#!/bin/bash
# TTS Server Control Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_SCRIPT="$SCRIPT_DIR/tts_server.py"

# Find Python 3.11+
if [ -x "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
elif [ -x "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON="/opt/homebrew/bin/python3"
else
    PYTHON="python3"
fi
PID_FILE="$HOME/.claude/tts_server.pid"
LOG_FILE="$HOME/.claude/tts_server.log"

case "$1" in
  start)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        echo "TTS server already running (PID: $PID)"
        exit 0
      fi
    fi
    echo "Starting TTS server..."
    nohup "$PYTHON" "$SERVER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    sleep 2
    if [ -f "$PID_FILE" ]; then
      echo "✅ TTS server started successfully"
      echo "📊 Monitor: tail -f $LOG_FILE"
    else
      echo "❌ Failed to start TTS server"
      exit 1
    fi
    ;;

  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      echo "Stopping TTS server (PID: $PID)..."
      kill "$PID" 2>/dev/null
      rm -f "$PID_FILE"
      echo "✅ TTS server stopped"
    else
      echo "TTS server not running"
    fi
    ;;

  restart)
    $0 stop
    sleep 1
    $0 start
    ;;

  status)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        echo "✅ TTS server is running (PID: $PID)"
        echo "📊 Log file: $LOG_FILE"
        if [ -f "$LOG_FILE" ]; then
          echo ""
          echo "Recent activity:"
          tail -5 "$LOG_FILE"
        fi
        exit 0
      else
        echo "❌ PID file exists but process not running"
        rm -f "$PID_FILE"
        exit 1
      fi
    else
      echo "❌ TTS server is not running"
      exit 1
    fi
    ;;

  logs)
    if [ -f "$LOG_FILE" ]; then
      tail -f "$LOG_FILE"
    else
      echo "No log file found"
      exit 1
    fi
    ;;

  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "Commands:"
    echo "  start    - Start the TTS server"
    echo "  stop     - Stop the TTS server"
    echo "  restart  - Restart the TTS server"
    echo "  status   - Check server status"
    echo "  logs     - Follow server logs"
    exit 1
    ;;
esac
