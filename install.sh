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
brew install python@3.12 portaudio hf ffmpeg

# Python environment setup
PYTHON_BIN="/opt/homebrew/bin/python3.12"

$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip

echo -e "${BLUE}installing dependencies${NC}"
pip install -r requirements.txt

# models download
echo -e "${BLUE}downloading models...${NC}"
mkdir -p models
hf download mlx-community/Mistral-Small-24B-instruct-2501-4bit --local-dir models/mistral-small-v3
hf download mlx-community/whisper-large-v3-turbo --local-dir models/whisper-large-v3-turbo

# launcher creation
cat <<EOF > neo
#!/bin/bash
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
\$(pwd)/venv/bin/python \$(pwd)/main.py "\$@"
EOF

chmod +x neo

echo -e "${GREEN}installation complete. start with: ./neo${NC}"