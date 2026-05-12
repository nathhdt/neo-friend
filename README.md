# neo-friend
macOS personal assistant using local ML-based models

## overview

neo-friend is a **local personal assistant for macOS**. it orchestrates a local gpt-oss-20b LLM using LangGraph and modular agents. the project is designed to run entirely on-device.

## quick start

### setup

```bash
./installer.sh
```

### usage

```bash
uv run neo
```

## technical stack

| component | technology |
| :--- | :--- |
| **LLM** | gpt-oss-20b via Ollama |
| **orchestration** | LangGraph |
| **STT** | Whisper Large v3 Turbo via MLX |
| **VAD** | Silero VAD |
| **TTS** | macOS `say` |
| **embeddings** | all-MiniLM-L6-v2 |
| **database** | LanceDB (conversation history) |

## modules

| module | description | requirement |
| :--- | :--- | :--- |
| **Proton Mail** | email management | Proton Mail Bridge |
| **macOS Calendars** | calendar integration | native access |
| **macOS Contacts** | contact list access | native access |
| **alarm** | smart wake-up with morning briefing | - |
| **weather** | weather data module | - |
| **utils** | general purpose utilities | - |

## platform support

- **hardware**: macOS Apple Silicon
- **memory**: 24GB RAM minimum
- **dependencies**: brew (Ollama, hf, portaudio, ffmpeg)
- **package manager**: uv

