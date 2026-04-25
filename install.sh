#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}starting neo installation...${NC}"

# Homebrew
if ! command -v brew &> /dev/null; then
    echo "error: Homebrew is not installed. please install it first at https://brew.sh/"
    exit 1
fi

# system dependencies
brew install python@3.12 ollama portaudio hf ffmpeg

# start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${BLUE}starting Ollama service...${NC}"
    ollama serve &
    sleep 3
fi

# pull LLM model
echo -e "${BLUE}pulling LLM...${NC}"
ollama pull mistral-small3.2:latest

# Python environment setup
PYTHON_BIN="/opt/homebrew/bin/python3.12"

$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip

echo -e "${BLUE}installing dependencies${NC}"
pip install -r requirements.txt

# STT model download (whisper stays on MLX)
echo -e "${BLUE}downloading whisper model...${NC}"
mkdir -p models
hf download mlx-community/whisper-large-v3-turbo --local-dir models/whisper-large-v3-turbo

# launcher creation
cat <<EOF > neo
#!/bin/bash
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
\$(pwd)/venv/bin/python \$(pwd)/main.py "\$@"
EOF

chmod +x neo

echo -e "${GREEN}installation complete. start with: ./neo${NC}"
echo -e "${GREEN}make sure Ollama is running: ollama serve${NC}"