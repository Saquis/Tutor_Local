saquis@SAQUIS:~$ mask() { sed -E 's/("[^"]*(key|token|secret|password)[^"]*"[[:space:]]*:[[:space:]]*")[^"]+/\1***TAPADO***/Ig'; }

# 1) el JSON actual, tapado
mask < ~/.openclaw/openclaw.json

# 2) comprobar que no quedó ninguna clave a la vista (no debe imprimir nada sospechoso)
mask < ~/.openclaw/openclaw.json | grep -nE "sk-|[A-Za-z0-9_-]{24,}"
{
  "agents": {
    "defaults": {
      "workspace": "/home/saquis/.openclaw/workspace",
      "model": {
        "primary": "deepseek/deepseek-flash",
        "fallbacks": []
      },
      "models": {
        "deepseek/deepseek-v4-pro": {
          "alias": "DeepSeek V4 Pro"
        },
        "deepseek/deepseek-flash": {
          "alias": "DeepSeek V4.1"
        }
      },
      "modelPolicy": {
        "allow": [
          "deepseek/deepseek-v4-pro",
          "deepseek/deepseek-flash",
          "openai/gpt-6-astra",
          "hive/deepseek-ai/deepseek-v4.1-flash"
        ]
      }
    },
    "entries": {
      "main": {}
    }
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "***TAPADO***"
    },
    "port": 18789,
    "bind": "loopback",
    "tailscale": {
      "mode": "off"
    },
    "nodes": {}
  },
  "session": {
    "dmScope": "per-channel-peer"
  },
  "tools": {
    "profile": "coding",
    "web": {
      "search": {
        "provider": "ollama",
        "enabled": true
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "ollama": {
        "baseUrl": "http://127.0.0.1:11434",
        "api": "ollama",
        "apiKey": "***TAPADO***",
        "models": [
          {
            "id": "gemma4",
            "name": "gemma4",
            "reasoning": false,
            "input": [
              "text"
            ],
            "cost": {
              "input": 0,
              "output": 0,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "contextWindow": 128000,
            "maxTokens": 8192,
            "params": {
              "num_ctx": 128000
            }
          },
          {
            "id": "mistral:latest",
            "name": "mistral:latest",
            "reasoning": false,
            "input": [
              "text"
            ],
            "cost": {
              "input": 0,
              "output": 0,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "contextWindow": 32768,
            "maxTokens": 8192,
            "params": {
              "num_ctx": 32768
            }
          }
        ]
      },
      "custom-api-groq-com": {
        "baseUrl": "https://api.groq.com/openai/v1",
        "api": "openai-completions",
        "apiKey": "***TAPADO***",
        "models": [
          {
            "id": "llama-3.3-70b-versatile",
            "name": "llama-3.3-70b-versatile (Custom Provider)",
            "contextWindow": 16000,
            "maxTokens": 4096,
            "input": [
              "text"
            ],
            "cost": {
              "input": 0,
              "output": 0,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "reasoning": false
          }
        ]
      },
      "deepseek": {
        "baseUrl": "https://api.deepseek.com",
        "apiKey": "***TAPADO***",
        "api": "openai-completions",
        "models": [
          {
            "id": "deepseek-flash",
            "name": "DeepSeek V4.1 Flash",
            "reasoning": true,
            "input": [
              "text",
              "image"
            ],
            "contextWindow": 1048576,
            "maxTokens": 393216,
            "cost": {
              "input": 0.28,
              "output": 0.42,
              "cacheRead": 0.028,
              "cacheWrite": 0
            },
            "compat": {
              "supportsUsageInStreaming": true
            },
            "api": "openai-completions"
          },
          {
            "id": "deepseek-v4-pro",
            "name": "DeepSeek V4 Pro",
            "reasoning": true,
            "input": [
              "text"
            ],
            "contextWindow": 1048576,
            "maxTokens": 393216,
            "cost": {
              "input": 0.28,
              "output": 0.42,
              "cacheRead": 0.028,
              "cacheWrite": 0
            },
            "compat": {
              "supportsUsageInStreaming": true
            },
            "api": "openai-completions"
          }
        ]
      },
      "openai": {
        "apiKey": {
          "source": "file",
          "provider": "openai_key_file",
          "id": "value"
        }
      },
      "hive": {
        "baseUrl": "https://api-cdn.thehive.ai/api/v3",
        "api": "openai-completions",
        "models": [
          {
            "id": "deepseek-ai/deepseek-v4.1-flash",
            "name": "DeepSeek V4.1 Flash (Hive)",
            "reasoning": false,
            "input": [
              "text",
              "image"
            ],
            "contextWindow": 1000000,
            "maxTokens": 65536
          }
        ],
        "apiKey": {
          "source": "file",
          "provider": "hive_key_file",
          "id": "value"
        }
      }
    }
  },
  "auth": {
    "profiles": {
      "google:default": {
        "provider": "google",
        "mode": "api_key"
      },
      "deepseek:default": {
        "provider": "deepseek",
        "mode": "api_key"
      }
    }
  },
  "channels": {
    "telegram": {
      "enabled": false,
      "botToken": "***TAPADO***",
      "dmPolicy": "allowlist",
      "allowFrom": [
        "5253885723"
      ],
      "groupAllowFrom": [
        "5253885723"
      ]
    }
  },
  "plugins": {
    "entries": {
      "ollama": {
        "enabled": true
      },
      "google": {
        "enabled": true
      },
      "deepseek": {
        "enabled": true
      },
      "groq": {
        "enabled": true
      },
      "codex": {
        "enabled": true
      }
    }
  },
  "wizard": {
    "lastRunAt": "2026-10-01T23:22:22.991Z",
    "lastRunVersion": "2026.7.1-2",
    "lastRunCommand": "doctor",
    "lastRunMode": "local"
  },
  "meta": {
    "lastTouchedVersion": "2026.9.7",
    "migrations": {
      "modelPolicyAllowlist": true,
      "utilityModelSeparation": true
    }
  },
  "skills": {
    "entries": {
      "1password": {
        "enabled": false
      },
      "blogwatcher": {
        "enabled": false
      },
      "blucli": {
        "enabled": false
      },
      "camsnap": {
        "enabled": false
      },
      "coding-agent": {
        "enabled": false
      },
      "eightctl": {
        "enabled": false
      },
      "gemini": {
        "enabled": false
      },
      "gh-issues": {
        "enabled": false
      },
      "gifgrep": {
        "enabled": false
      },
      "github": {
        "enabled": false
      },
      "gog": {
        "enabled": false
      },
      "goplaces": {
        "enabled": false
      },
      "himalaya": {
        "enabled": false
      },
      "mcporter": {
        "enabled": false
      },
      "nano-pdf": {
        "enabled": false
      },
      "obsidian": {
        "enabled": false
      },
      "openai-whisper": {
        "enabled": false
      },
      "openai-whisper-api": {
        "enabled": false
      },
      "openhue": {
        "enabled": false
      },
      "oracle": {
        "enabled": false
      },
      "ordercli": {
        "enabled": false
      },
      "sag": {
        "enabled": false
      },
      "session-logs": {
        "enabled": false
      },
      "sherpa-onnx-tts": {
        "enabled": false
      },
      "songsee": {
        "enabled": false
      },
      "sonoscli": {
        "enabled": false
      },
      "spotify-player": {
        "enabled": false
      },
      "summarize": {
        "enabled": false
      },
      "trello": {
        "enabled": false
      },
      "video-frames": {
        "enabled": false
      },
      "xurl": {
        "enabled": false
      },
      "model-usage": {
        "enabled": false
      }
    }
  },
  "update": {
    "channel": "stable"
  },
  "memory": {
    "search": {
      "provider": "ollama",
      "model": "nomic-embed-text"
    }
  },
  "secrets": {
    "providers": {
      "openai_key_file": {
        "source": "file",
        "path": "/home/saquis/.config/openai.key",
        "mode": "singleValue"
      },
      "hive_key_file": {
        "source": "file",
        "path": "/home/saquis/.config/hive.key",
        "mode": "singleValue"
      }
    }
  }
}
148:              "supportsUsageInStreaming": true
168:              "supportsUsageInStreaming": true
saquis@SAQUIS:~$