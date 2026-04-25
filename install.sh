#!/bin/bash

set -euo pipefail

GREEN='\033[0;92m'
BLUE='\033[0;96m'
RED='\033[0;91m'
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
    echo -e "\r${BLUE}[hw] ${GREEN}[ok]${BLUE} apple silicon hardware - requirement satisfied${RESET}"
else
    echo -e "\r${RED}[hw] error: this agent is optimized for macOS on Apple Silicon (arm64)${RESET}"
    exit 1
fi

# RAM Check
echo -ne "${BLUE}[hw] [..] checking system RAM...${RESET}"
TOTAL_RAM_GB=$(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024))
if [ "$TOTAL_RAM_GB" -ge 16 ]; then
    echo -e "\r${BLUE}[hw] ${GREEN}[ok]${BLUE} ${TOTAL_RAM_GB}gb ram - requirement satisfied${RESET}"
else
    echo -e "\r${RED}[hw] error: 16GB of RAM is the minimum recommended to run this agent. detected: ${TOTAL_RAM_GB}GB${RESET}"
    exit 1
fi

# system dependencies
echo -ne "${BLUE}[sys] [..] checking Homebrew installation...${RESET}"
if command -v brew &> /dev/null; then
    echo -e "\r\033[K${BLUE}[sys] ${GREEN}[ok]${BLUE} Homebrew is installed${RESET}"
else
    echo -e "\r${RED}[sys] error: Homebrew is not installed. please install it first at https://brew.sh/${RESET}"
    exit 1
fi

DEPENDENCIES=(python@3.12 ollama hf portaudio ffmpeg)

for pkg in "${DEPENDENCIES[@]}"; do
    if brew list "$pkg" &>/dev/null; then
        echo -e "${BLUE}[sys] ${GREEN}[ok]${BLUE} $pkg is already installed"
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

    echo -e "\r${BLUE}[llm] ${GREEN}[ok]${BLUE} Ollama service is running${RESET}"
else
    echo -e "${BLUE}[llm] ${GREEN}[ok]${BLUE} Ollama service already running${RESET}"
fi

# LLM model pull
MODEL_NAME=$(sed -n '/llm:/,/^[a-zA-Z]/p' config.yaml | grep "model:" | head -n 1 | sed 's/.*model:[[:space:]]*//' | tr -d '\r\n[:space:]')
if [ -z "$MODEL_NAME" ]; then
    echo -e "${RED}[llm] error: could not parse model name from config.yaml${RESET}"
    exit 1
fi
echo -ne "${BLUE}[llm] [..] pulling model ($MODEL_NAME)...${RESET}"
if ollama pull "$MODEL_NAME" > /dev/null 2>&1; then
    echo -e "\r\033[K${BLUE}[llm] ${GREEN}[ok]${BLUE} model ready: $MODEL_NAME${RESET}"
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
    echo -e "\r\033[K${BLUE}[stt] ${GREEN}[ok]${BLUE} model ready: $STT_MODEL${RESET}"
else
    echo -e "\r\033[K${RED}[stt] error: failed to pull model${RESET}"
    exit 1
fi

# Python environment setup
PYTHON_BIN="/opt/homebrew/bin/python3.12"
if [ ! -x "$PYTHON_BIN" ]; then
    echo -e "${RED}[python] python3.12 not found${RESET}"
    exit 1
fi
$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1

# Python dependencies
while read -r lib || [[ -n "$lib" ]]; do
    [[ -z "$lib" || "$lib" =~ ^# ]] && continue
    
    lib_name=$(echo "$lib" | cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1)
    
    if pip show "$lib_name" &>/dev/null; then
        echo -e "${BLUE}[python] ${GREEN}[ok]${BLUE} $lib_name is already installed"
    else
        echo -ne "${BLUE}[python] [..] installing $lib...${RESET}"
        pip install "$lib" > /dev/null 2>&1
        echo -e "\r${BLUE}[python] ${GREEN}[ok]${BLUE} $lib installed             "
    fi
done < requirements.txt

# llm warmup
echo -ne "${BLUE}[warmup] [..] warming up LLM model...${RESET}"
if echo "hi" | ollama run "$MODEL_NAME" > /dev/null 2>&1; then
    echo -e "\r${BLUE}[warmup] ${GREEN}[ok]${BLUE} LLM model warmed up        ${RESET}"
else
    echo -e "\r${RED}[warmup] error: failed to warmup LLM${RESET}"
fi

# openWakeWord warmup
echo -ne "${BLUE}[warmup] [..] warming up openWakeWord...${RESET}"
if python - <<EOF > /dev/null 2>&1
from core.wake import WakeWord
WakeWord()
EOF
then
    echo -e "\r${BLUE}[warmup] ${GREEN}[ok]${BLUE} openWakeWord warmed up      ${RESET}"
else
    echo -e "\r${RED}[warmup] error: openWakeWord warmup failed${RESET}"
fi

# launcher creation
cat <<EOF > neo
#!/bin/bash
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
\$(pwd)/venv/bin/python \$(pwd)/main.py "\$@"
EOF

chmod +x neo

echo -e "${BLUE}installation complete, start with: ./neo${RESET}"