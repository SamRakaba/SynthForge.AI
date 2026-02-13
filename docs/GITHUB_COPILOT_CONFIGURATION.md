# GitHub Copilot Agent Configuration Guide

**Last Updated:** February 13, 2026  
**Audience:** Developers using GitHub Copilot with SynthForge.AI

---

## Overview

This guide explains how to configure GitHub Copilot (the AI coding assistant) to work effectively with the SynthForge.AI repository. It covers:

1. **Model Configuration** - Which AI models Copilot can use and how to configure them
2. **MCP Server Management** - How to list, add, and configure Model Context Protocol (MCP) servers
3. **Configuration Scope** - Understanding global vs. repository-specific settings

---

## Table of Contents

- [Model Configuration](#model-configuration)
- [MCP Server Management](#mcp-server-management)
- [Configuration Scope](#configuration-scope)
- [Practical Examples for SynthForge.AI](#practical-examples-for-synthforgeai)
- [Troubleshooting](#troubleshooting)
- [References](#references)

---

## Model Configuration

### Available Models

GitHub Copilot supports multiple AI models depending on your subscription tier:

| Model | Availability | Use Case | Performance |
|-------|--------------|----------|-------------|
| **GPT-4** | Copilot Individual/Business/Enterprise | Complex reasoning, architecture decisions | Highest quality, slower |
| **GPT-3.5-turbo** | Copilot Individual/Business/Enterprise | Quick completions, simple tasks | Fast, good quality |
| **Claude 3.5 Sonnet** | Copilot Enterprise (select plans) | Code analysis, refactoring | High quality, fast |
| **o1-preview** | Copilot Enterprise (select plans) | Advanced reasoning, complex problems | Highest reasoning, slower |
| **o1-mini** | Copilot Enterprise (select plans) | Fast reasoning tasks | Fast reasoning |

### How to Configure Models

#### In VS Code / VS Code Insiders

1. **Access Settings:**
   - Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
   - Type: `Preferences: Open Settings (UI)`
   - Search for: `github.copilot`

2. **Configure Model:**
   ```json
   // settings.json
   {
     "github.copilot.editor.enableAutoCompletions": true,
     "github.copilot.advanced": {
       "model": "gpt-4"  // Options: "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"
     }
   }
   ```

3. **Per-Request Model Selection (Copilot Chat):**
   - In Copilot Chat, you can specify the model inline:
   ```
   @workspace /explain using gpt-4
   @workspace /fix using claude-3-sonnet
   ```

#### In JetBrains IDEs (IntelliJ, PyCharm, etc.)

1. **Open Settings:**
   - Go to `Settings` > `Tools` > `GitHub Copilot`

2. **Configure Model:**
   - Select your preferred model from the dropdown
   - Available options depend on your subscription

3. **Apply Changes:**
   - Click `OK` to save settings

#### Via GitHub Copilot CLI

```bash
# Check current model
gh copilot config get model

# Set model
gh copilot config set model gpt-4

# Available options:
# - gpt-4
# - gpt-3.5-turbo
# - claude-3-sonnet (if available)
```

### Model Selection Best Practices

**For SynthForge.AI Development:**

- **Architecture & Design Decisions:** Use GPT-4 or o1-preview
  ```
  @workspace Explain the agent architecture using gpt-4
  ```

- **Code Completion & Simple Edits:** Use GPT-3.5-turbo (faster)
  ```
  # Default model for inline completions
  ```

- **Complex Refactoring:** Use GPT-4 or Claude 3.5 Sonnet
  ```
  @workspace /fix Refactor the agent initialization using claude-3-sonnet
  ```

- **Azure-Specific Questions:** Use GPT-4 (better Azure knowledge)
  ```
  @workspace What Azure services does this diagram use? (uses GPT-4)
  ```

---

## MCP Server Management

### What are MCP Servers?

Model Context Protocol (MCP) servers provide GitHub Copilot with access to external tools, APIs, and documentation. For SynthForge.AI, MCP servers enable Copilot to:

- Access Azure documentation (Microsoft Learn MCP)
- Query Bicep templates and Azure Verified Modules
- Search Terraform Registry
- Look up GitHub Actions and Azure DevOps pipelines

### Configuration Location

MCP servers are configured in **GitHub Copilot settings**, which can be:
- **Global** (applies to all repositories)
- **Workspace-specific** (applies to current workspace/repository)

### How to List MCP Servers

#### VS Code / VS Code Insiders

1. **Via Command Palette:**
   ```
   Ctrl+Shift+P / Cmd+Shift+P
   > GitHub Copilot: Show MCP Server Status
   ```

2. **Via Settings UI:**
   - Open Settings (`Ctrl+,` or `Cmd+,`)
   - Search: `github.copilot.mcp`
   - View configured servers under `Github > Copilot > MCP: Servers`

3. **Via settings.json:**
   ```json
   // .vscode/settings.json or User settings.json
   {
     "github.copilot.mcp.servers": {
       // Lists all configured MCP servers
     }
   }
   ```

#### GitHub Copilot CLI

```bash
# List all configured MCP servers
gh copilot mcp list

# Show detailed status
gh copilot mcp status
```

### How to Add MCP Servers

#### Method 1: VS Code Settings UI

1. Open Settings (`Ctrl+,` or `Cmd+,`)
2. Search for: `github.copilot.mcp.servers`
3. Click `Edit in settings.json`
4. Add server configuration:

```json
{
  "github.copilot.mcp.servers": {
    "mslearn": {
      "url": "https://mcp.ai.azure.com",
      "description": "Microsoft Learn documentation and Azure resources",
      "enabled": true
    },
    "bicep": {
      "url": "http://localhost:3101",
      "description": "Bicep templates and Azure Verified Modules",
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@microsoft/mcp-server-bicep"]
    },
    "terraform": {
      "url": "http://localhost:3102",
      "description": "HashiCorp Terraform Registry and providers",
      "enabled": true,
      "command": "docker",
      "args": ["run", "-p", "3102:3102", "hashicorp/terraform-mcp-server"]
    }
  }
}
```

#### Method 2: GitHub Copilot CLI

```bash
# Add a remote MCP server
gh copilot mcp add mslearn --url https://mcp.ai.azure.com

# Add a local MCP server with command
gh copilot mcp add bicep \
  --command "npx -y @microsoft/mcp-server-bicep" \
  --url http://localhost:3101

# Add with authentication
gh copilot mcp add azure \
  --url http://localhost:3100 \
  --token "$AZURE_TOKEN"
```

#### Method 3: Direct settings.json Edit

**Global Configuration** (~/.config/Code/User/settings.json):
```json
{
  "github.copilot.mcp.servers": {
    "mslearn": {
      "url": "https://mcp.ai.azure.com",
      "enabled": true
    }
  }
}
```

**Workspace Configuration** (.vscode/settings.json in repository):
```json
{
  "github.copilot.mcp.servers": {
    "bicep": {
      "url": "http://localhost:3101",
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@microsoft/mcp-server-bicep"]
    }
  }
}
```

### MCP Server Configuration Schema

```json
{
  "github.copilot.mcp.servers": {
    "<server-name>": {
      // REQUIRED: Server URL
      "url": "https://example.com/mcp",
      
      // REQUIRED: Enable/disable server
      "enabled": true,
      
      // OPTIONAL: Human-readable description
      "description": "Server description",
      
      // OPTIONAL: Command to start local server
      "command": "npx",
      "args": ["-y", "@package/mcp-server"],
      
      // OPTIONAL: Environment variables
      "env": {
        "API_KEY": "${env:MY_API_KEY}",
        "DEBUG": "true"
      },
      
      // OPTIONAL: Authentication
      "auth": {
        "type": "bearer",
        "token": "${env:MCP_TOKEN}"
      },
      
      // OPTIONAL: Connection settings
      "timeout": 30000,
      "retries": 3
    }
  }
}
```

### How to Remove MCP Servers

#### VS Code

1. Open `settings.json`
2. Remove the server entry from `github.copilot.mcp.servers`
3. Or set `"enabled": false` to temporarily disable

#### GitHub Copilot CLI

```bash
# Remove server
gh copilot mcp remove bicep

# Disable server (keeps configuration)
gh copilot mcp disable bicep

# Re-enable server
gh copilot mcp enable bicep
```

---

## Configuration Scope

### Understanding Configuration Hierarchy

GitHub Copilot settings follow this priority (highest to lowest):

1. **Workspace Settings** (`.vscode/settings.json` in repository)
   - Applies only to the current repository
   - Overrides user settings
   - Committed to version control (can be shared with team)

2. **User Settings** (`~/.config/Code/User/settings.json`)
   - Applies to all repositories for current user
   - Global configuration
   - Not shared with team

3. **Default Settings**
   - Built-in Copilot defaults
   - Used when no custom configuration exists

### Global vs. Repository-Specific Configuration

#### When to Use Global Configuration

✅ **Use Global Settings For:**
- Personal model preferences (GPT-4 vs GPT-3.5)
- MCP servers you use across all projects (e.g., Microsoft Learn)
- General Copilot behavior preferences
- Authentication tokens (keep in user settings, not in repo)

**Example - User Settings (~/.config/Code/User/settings.json):**
```json
{
  "github.copilot.advanced": {
    "model": "gpt-4"
  },
  "github.copilot.mcp.servers": {
    "mslearn": {
      "url": "https://mcp.ai.azure.com",
      "enabled": true
    }
  }
}
```

#### When to Use Repository-Specific Configuration

✅ **Use Workspace Settings For:**
- Project-specific MCP servers
- Team-wide conventions
- Repository-specific model recommendations
- Project-specific Copilot behaviors

**Example - Workspace Settings (.vscode/settings.json):**
```json
{
  "github.copilot.mcp.servers": {
    "bicep": {
      "url": "http://localhost:3101",
      "description": "Bicep MCP for SynthForge.AI IaC generation",
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@microsoft/mcp-server-bicep"]
    },
    "terraform": {
      "url": "http://localhost:3102",
      "description": "Terraform MCP for SynthForge.AI IaC generation",
      "enabled": true
    }
  },
  "github.copilot.editor.enableAutoCompletions": true
}
```

### Configuration Merging

When both global and workspace settings exist:
- Workspace settings **override** global settings for the same keys
- Different settings are **merged** (both apply)

**Example:**

**Global Settings:**
```json
{
  "github.copilot.advanced": {"model": "gpt-4"},
  "github.copilot.mcp.servers": {
    "mslearn": {"url": "https://mcp.ai.azure.com", "enabled": true}
  }
}
```

**Workspace Settings:**
```json
{
  "github.copilot.mcp.servers": {
    "bicep": {"url": "http://localhost:3101", "enabled": true}
  }
}
```

**Effective Configuration (Merged):**
```json
{
  "github.copilot.advanced": {"model": "gpt-4"},
  "github.copilot.mcp.servers": {
    "mslearn": {"url": "https://mcp.ai.azure.com", "enabled": true},
    "bicep": {"url": "http://localhost:3101", "enabled": true}
  }
}
```

---

## Practical Examples for SynthForge.AI

### Recommended Configuration for Contributors

#### 1. Create Workspace Settings

Create `.vscode/settings.json` in the repository root:

```json
{
  "github.copilot.mcp.servers": {
    "mslearn": {
      "url": "https://mcp.ai.azure.com",
      "description": "Microsoft Learn - Azure documentation and schemas",
      "enabled": true
    },
    "bicep": {
      "url": "http://localhost:3101",
      "description": "Bicep MCP - Azure Verified Modules and best practices",
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@microsoft/mcp-server-bicep"]
    },
    "terraform": {
      "url": "http://localhost:3102",
      "description": "Terraform MCP - HashiCorp Registry and providers",
      "enabled": false,
      "command": "docker",
      "args": ["run", "-p", "3102:3102", "hashicorp/terraform-mcp-server"]
    },
    "github": {
      "url": "https://api.githubcopilot.com/mcp",
      "description": "GitHub Actions and workflow templates",
      "enabled": true
    }
  },
  "github.copilot.advanced": {
    "model": "gpt-4"
  },
  "github.copilot.editor.enableAutoCompletions": true,
  "files.associations": {
    "*.yaml": "yaml",
    "*.bicep": "bicep"
  }
}
```

#### 2. Start Local MCP Servers

**For Bicep Development:**
```bash
# Terminal 1 - Start Bicep MCP server
npx -y @microsoft/mcp-server-bicep

# Or use VS Code MCP extension
# Install: ms-azuretools.vscode-azure-mcp-server
```

**For Terraform Development:**
```bash
# Terminal 2 - Start Terraform MCP server
docker run -p 3102:3102 hashicorp/terraform-mcp-server

# Optional: Set HCP Terraform token
export TFE_TOKEN=your-token-here
```

#### 3. Verify Configuration

In VS Code:
1. Open Command Palette (`Ctrl+Shift+P`)
2. Run: `GitHub Copilot: Show MCP Server Status`
3. Verify all enabled servers show ✅ Connected

Or via CLI:
```bash
gh copilot mcp status
```

### Example Copilot Chat Commands with MCP

**Using Microsoft Learn MCP:**
```
@workspace What are the VNet integration requirements for Azure Functions?
```

**Using Bicep MCP:**
```
@workspace Generate a Bicep module for Azure App Service with VNet integration
```

**Using Terraform MCP:**
```
@workspace Find Terraform modules for Azure Virtual Network
```

**Multi-MCP Query:**
```
@workspace Compare Bicep vs Terraform for deploying Azure App Service
```

### Team Collaboration

**Option 1: Commit Workspace Settings (Recommended)**
```bash
# Add to version control
git add .vscode/settings.json
git commit -m "Add GitHub Copilot MCP configuration for SynthForge.AI"
git push
```

**Benefits:**
- All team members get the same MCP servers
- Consistent Copilot experience across team
- Easy onboarding for new contributors

**Option 2: Document in README (Alternative)**

Add to README.md:
```markdown
## GitHub Copilot Setup

To get the best experience with GitHub Copilot:

1. Add these MCP servers to your settings:
   - Microsoft Learn: `https://mcp.ai.azure.com`
   - Bicep MCP: `npx -y @microsoft/mcp-server-bicep`
   
2. Use GPT-4 model for architecture decisions
3. See `docs/GITHUB_COPILOT_CONFIGURATION.md` for details
```

---

## Troubleshooting

### MCP Server Connection Issues

**Problem:** MCP server shows as disconnected

**Solutions:**
```bash
# 1. Check if server is running
curl http://localhost:3101/health

# 2. Verify URL in settings
# Check .vscode/settings.json for correct URL

# 3. Restart server
# Kill the process and restart

# 4. Check logs
# VS Code: Output > GitHub Copilot
# Look for MCP connection errors

# 5. Test with CLI
gh copilot mcp test bicep
```

### Model Not Available

**Problem:** Selected model not available in Copilot

**Solutions:**
1. Check your GitHub Copilot subscription tier
2. Verify model name spelling in settings
3. Try default model (remove model setting)
4. Contact GitHub support for enterprise features

### Authentication Errors

**Problem:** MCP server requires authentication

**Solutions:**
```json
{
  "github.copilot.mcp.servers": {
    "azure": {
      "url": "http://localhost:3100",
      "auth": {
        "type": "bearer",
        "token": "${env:AZURE_TOKEN}"
      }
    }
  }
}
```

```bash
# Set environment variable
export AZURE_TOKEN=your-token-here

# Or in VS Code settings
"terminal.integrated.env.linux": {
  "AZURE_TOKEN": "your-token-here"
}
```

### Performance Issues

**Problem:** Copilot is slow with MCP servers

**Solutions:**
1. Disable unused MCP servers:
   ```json
   {"enabled": false}
   ```

2. Use faster model for completions:
   ```json
   {"github.copilot.advanced": {"model": "gpt-3.5-turbo"}}
   ```

3. Increase timeout:
   ```json
   {
     "github.copilot.mcp.servers": {
       "slow-server": {
         "timeout": 60000,
         "retries": 1
       }
     }
   }
   ```

---

## References

### Official Documentation

- **GitHub Copilot Documentation:**
  - [Getting Started](https://docs.github.com/en/copilot/getting-started-with-github-copilot)
  - [Configuring GitHub Copilot](https://docs.github.com/en/copilot/configuring-github-copilot)
  - [MCP Integration](https://docs.github.com/en/copilot/mcp)

- **Model Context Protocol (MCP):**
  - [MCP Specification](https://modelcontextprotocol.io)
  - [Microsoft MCP Servers](https://github.com/microsoft/mcp)
  - [Azure AI Foundry MCP](https://learn.microsoft.com/azure/ai-foundry/mcp/get-started)

### SynthForge.AI Specific

- **Related Documentation:**
  - [.env.example](../.env.example) - Environment configuration for SynthForge.AI agents with MCP server setup
  - [README.md](../README.md) - Project overview and setup
  - [Phase 2 Prerequisites](PHASE2_PREREQUISITES.md) - Additional MCP server information for IaC generation

- **Key Differences:**
  - This guide covers **GitHub Copilot** (your IDE assistant)
  - .env.example covers **SynthForge.AI agents** (the application)
  - Both can use MCP servers, but configurations are separate

### Community Resources

- **VS Code Marketplace:**
  - [GitHub Copilot Extension](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)
  - [Azure MCP Server Extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azure-mcp-server)

- **GitHub Discussions:**
  - [Copilot Community](https://github.com/community/community/discussions/categories/copilot)
  - [MCP Community](https://github.com/modelcontextprotocol/community)

---

## Summary

### Key Takeaways

1. **Models:**
   - Configure via `github.copilot.advanced.model` in settings
   - Choose GPT-4 for complex tasks, GPT-3.5-turbo for speed
   - Model availability depends on subscription tier

2. **MCP Servers:**
   - Add via `github.copilot.mcp.servers` in settings.json
   - Can be global (user settings) or workspace-specific (.vscode/settings.json)
   - Multiple servers can be enabled simultaneously

3. **Configuration Scope:**
   - **Global:** User settings (~/.config/Code/User/settings.json)
   - **Repository:** Workspace settings (.vscode/settings.json)
   - Workspace settings override global settings
   - Commit workspace settings for team consistency

### Quick Start Checklist

For new SynthForge.AI contributors:

- [ ] Install GitHub Copilot extension in VS Code
- [ ] Configure model preference (recommended: GPT-4)
- [ ] Add Microsoft Learn MCP server
- [ ] Start Bicep MCP server (if doing IaC work)
- [ ] Verify MCP server connections
- [ ] Test with sample Copilot chat commands

---

**Questions?** Open an issue or discussion in the repository.

**Contributing:** If you discover additional MCP servers or configuration tips, please update this document.
