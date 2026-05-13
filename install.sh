#!/bin/bash

set -euo pipefail

PINK='\033[38;2;245;194;231m'
BLUE='\033[38;2;137;180;250m'
SKY='\033[38;2;137;220;235m'
RED='\033[38;2;243;139;168m'
RESET='\033[0m'

prefix() {
    local tag="$1"
    while IFS= read -r line; do
        echo -e "${BLUE}${tag} ${line}${RESET}"
    done
}

echo -e "${BLUE}starting neo installation...${RESET}"

# Apple Silicon check
echo -ne "${BLUE}[hw] [..] checking apple silicon hardware...${RESET}"
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo -e "\r${BLUE}[hw] ${PINK}[ok]${BLUE} apple silicon hardware - requirement satisfied${RESET}"
else
    echo -e "\r${RED}[hw] error: this agent is optimized for macOS on Apple Silicon (arm64)${RESET}"
    exit 1
fi

# RAM Check
echo -ne "${BLUE}[hw] [..] checking system RAM...${RESET}"
TOTAL_RAM_GB=$(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024))
if [ "$TOTAL_RAM_GB" -ge 16 ]; then
    echo -e "\r${BLUE}[hw] ${PINK}[ok]${BLUE} ${TOTAL_RAM_GB}gb ram - requirement satisfied${RESET}"
else
    echo -e "\r${RED}[hw] error: 16GB of RAM is the minimum recommended to run this agent. detected: ${TOTAL_RAM_GB}GB${RESET}"
    exit 1
fi

# system dependencies
echo -ne "${BLUE}[sys] [..] checking Homebrew installation...${RESET}"
if command -v brew &> /dev/null; then
    echo -e "\r\033[K${BLUE}[sys] ${PINK}[ok]${BLUE} Homebrew is installed${RESET}"
else
    echo -e "\r${RED}[sys] error: Homebrew is not installed. please install it first at https://brew.sh/${RESET}"
    exit 1
fi

DEPENDENCIES=(ollama hf portaudio ffmpeg)

for pkg in "${DEPENDENCIES[@]}"; do
    if brew list "$pkg" &>/dev/null; then
        echo -e "${BLUE}[sys] ${PINK}[ok]${BLUE} $pkg is already installed"
    else
        echo -e "${BLUE}[sys] [..] installing $pkg..."
        brew install "$pkg" 2>&1 | prefix "[sys]"
    fi
done

# Ollama service start
if ! pgrep -x "ollama" > /dev/null; then
    echo -ne "${BLUE}[llm] [..] starting Ollama service...${RESET}"
    
    ollama serve >/dev/null 2>&1 &
    
    until curl -s http://localhost:11434 > /dev/null; do
        sleep 1
    done

    echo -e "\r${BLUE}[llm] ${PINK}[ok]${BLUE} Ollama service is running${RESET}"
else
    echo -e "${BLUE}[llm] ${PINK}[ok]${BLUE} Ollama service already running${RESET}"
fi

# LLM model pull
MODEL_NAME=$(sed -n '/llm:/,/^[a-zA-Z]/p' config.yaml | grep "model:" | head -n 1 | sed 's/.*model:[[:space:]]*//' | tr -d '\r\n[:space:]')
if [ -z "$MODEL_NAME" ]; then
    echo -e "${RED}[llm] error: could not parse model name from config.yaml${RESET}"
    exit 1
fi
echo -ne "${BLUE}[llm] [..] pulling model ($MODEL_NAME)...${RESET}"
if ollama pull "$MODEL_NAME" > /dev/null 2>&1; then
    echo -e "\r\033[K${BLUE}[llm] ${PINK}[ok]${BLUE} model ready: $MODEL_NAME${RESET}"
else
    echo -e "\r\033[K${RED}[llm] error: failed to pull model${RESET}"
    exit 1
fi

# STT model pull
STT_BLOCK=$(sed -n '/stt:/,/^[a-zA-Z]/p' config.yaml)
STT_MODEL=$(echo "$STT_BLOCK" | grep "model:" | head -n 1 | sed 's/.*model:[[:space:]]*//' | tr -d '\r\n[:space:]')
STT_LOCATION=$(echo "$STT_BLOCK" | grep "location:" | head -n 1 | sed 's/.*location:[[:space:]]*//' | tr -d '\r\n[:space:]')
if [ -z "$STT_MODEL" ] || [ -z "$STT_LOCATION" ]; then
    echo -e "${RED}[stt] error: could not parse STT config from config.yaml${RESET}"
    exit 1
fi
STT_TARGET_DIR="$STT_LOCATION/$STT_MODEL"
echo -ne "${BLUE}[stt] [..] pulling model ($STT_MODEL)...${RESET}"
mkdir -p "$STT_TARGET_DIR"
if stdbuf -oL -eL hf download "$STT_MODEL" \
    --local-dir "$STT_TARGET_DIR" > /dev/null 2>&1; then
    echo -e "\r\033[K${BLUE}[stt] ${PINK}[ok]${BLUE} model ready: $STT_MODEL${RESET}"
else
    echo -e "\r\033[K${RED}[stt] error: failed to pull model${RESET}"
    exit 1
fi

# embedding model pull
MEMORY_BLOCK=$(sed -n '/^memory:/,/^[a-zA-Z]/p' config.yaml)
MEMORY_MODEL=$(echo "$MEMORY_BLOCK" | grep "model:" | head -n 1 | sed 's/.*model:[[:space:]]*//' | tr -d '\r\n[:space:]')
MEMORY_LOCATION=$(echo "$MEMORY_BLOCK" | grep "location:" | head -n 1 | sed 's/.*location:[[:space:]]*//' | tr -d '\r\n[:space:]')
if [ -z "$MEMORY_MODEL" ] || [ -z "$MEMORY_LOCATION" ]; then
    echo -e "${RED}[memory] error: could not parse memory config from config.yaml${RESET}"
    exit 1
fi
MEMORY_TARGET_DIR="$MEMORY_LOCATION/$MEMORY_MODEL"
echo -ne "${BLUE}[memory] [..] pulling model ($MEMORY_MODEL)...${RESET}"
mkdir -p "$MEMORY_TARGET_DIR"
if stdbuf -oL -eL hf download "$MEMORY_MODEL" \
    --local-dir "$MEMORY_TARGET_DIR" > /dev/null 2>&1; then
    echo -e "\r\033[K${BLUE}[memory] ${PINK}[ok]${BLUE} model ready: $MEMORY_MODEL${RESET}"
else
    echo -e "\r\033[K${RED}[memory] error: failed to pull model${RESET}"
    exit 1
fi

# uv package manager
echo -ne "${BLUE}[sys] [..] checking uv installation...${RESET}"
if command -v uv &> /dev/null; then
    echo -e "\r\033[K${BLUE}[sys] ${PINK}[ok]${BLUE} uv is already installed${RESET}"
else
    echo -e "\r\033[K${BLUE}[sys] [..] installing uv...${RESET}"
    curl -LsSf https://astral.sh/uv/install.sh | sh 2>&1 | prefix "[sys]"
    source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
    echo -e "${BLUE}[sys] ${PINK}[ok]${BLUE} uv installed${RESET}"
fi

# Python environment + dependencies
echo -ne "${BLUE}[python] [..] syncing environment and dependencies...${RESET}"
if uv sync --python 3.12 > /dev/null 2>&1; then
    echo -e "\r\033[K${BLUE}[python] ${PINK}[ok]${BLUE} environment ready, all dependencies installed${RESET}"
else
    echo -e "\r\033[K${RED}[python] error: failed to sync dependencies${RESET}"
    exit 1
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

# macOS calendar permission
echo -ne "${BLUE}[permissions] [..] requesting calendar access...${RESET}"
if .venv/bin/python - <<EOF > /dev/null 2>&1
from neo.modules.calendar.module import CalendarModule
m = CalendarModule()
m.on_load()
EOF
then
    echo -e "\r${BLUE}[permissions] ${PINK}[ok]${BLUE} macOS calendar access granted        ${RESET}"
else
    echo -e "\r${RED}[permissions] error: macOS calendar access denied — authorize in System Settings → Privacy → Calendars${RESET}"
fi

# macOS contacts permission
echo -ne "${BLUE}[permissions] [..] requesting macOS contacts access...${RESET}"
if .venv/bin/python - <<EOF > /dev/null 2>&1
from neo.modules.contacts.module import ContactsModule
m = ContactsModule()
m.on_load()
EOF
then
    echo -e "\r${BLUE}[permissions] ${PINK}[ok]${BLUE} macOS contacts access granted                ${RESET}"
else
    echo -e "\r${RED}[permissions] error: macOS contacts access denied — authorize in System Settings → Privacy → Contacts${RESET}"
fi

# llm warmup
echo -ne "${BLUE}[warmup] [..] warming up LLM model...${RESET}"
if echo "hi" | ollama run "$MODEL_NAME" > /dev/null 2>&1; then
    echo -e "\r${BLUE}[warmup] ${PINK}[ok]${BLUE} LLM model warmed up        ${RESET}"
else
    echo -e "\r${RED}[warmup] error: failed to warmup LLM${RESET}"
fi

# openWakeWord warmup
echo -ne "${BLUE}[warmup] [..] warming up openWakeWord...${RESET}"
if uv run python - <<EOF > /dev/null 2>&1
from neo.adapters.wake import WakeWord
WakeWord()
EOF
then
    echo -e "\r${BLUE}[warmup] ${PINK}[ok]${BLUE} openWakeWord warmed up      ${RESET}"
else
    echo -e "\r${RED}[warmup] error: openWakeWord warmup failed${RESET}"
fi

# memory warmup
echo -ne "${BLUE}[warmup] [..] warming up memory...${RESET}"
if uv run python - <<EOF > /dev/null 2>&1
from neo.adapters.lancedb_memory import MemoryManager
MemoryManager()
EOF
then
    echo -e "\r${BLUE}[warmup] ${PINK}[ok]${BLUE} memory warmed up            ${RESET}"
else
    echo -e "\r${RED}[warmup] error: memory warmup failed${RESET}"
fi

echo -e "${BLUE}installation complete, start with: ${SKY}uv run neo${RESET}"
