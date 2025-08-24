# Sunflower AI + Open WebUI Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Initial Setup
```bash
# Clone or extract your Sunflower AI repository
cd sunflower-ai

# Install Python dependencies
pip install -r requirements.txt

# Run the universal launcher
python UNIVERSAL_LAUNCHER.py
```

**OR** for immediate start:
- **Windows**: Double-click `windows_launcher.bat`
- **macOS**: Run `bash macos_launcher.sh`

### Step 2: First Run
1. The system will automatically:
   - Install Open WebUI
   - Download/start Ollama
   - Create data directories
   - Generate admin password (SAVE THIS!)

2. Browser opens to `http://localhost:8080`

3. Create your parent account using the generated password

### Step 3: Add Child Profiles
1. Open Parent Dashboard: `http://localhost:8080/settings`
2. Click "Add Child Profile"
3. Enter:
   - Child's name
   - Age (determines safety level)
   - Grade level

### Step 4: Start Learning!
1. Select child profile from dropdown
2. AI automatically adjusts to age level
3. All conversations are filtered and logged

---

## 📁 Project Structure

```
sunflower-ai/
├── 📄 UNIVERSAL_LAUNCHER.py          # Main entry point (GUI)
├── 📄 openwebui_integration.py       # Core integration manager
├── 📄 openwebui_config.py           # Configuration manager
├── 📄 safety_filter.py              # Content moderation
├── 📂 launchers/
│   ├── windows_launcher.bat        # Windows quick start
│   └── macos_launcher.sh          # macOS quick start
├── 📂 modelfiles/
│   ├── Sunflower_AI_Kids.modelfile    # Kids model (ages 5-13)
│   └── Sunflower_AI_Educator.modelfile # Educator model
├── 📂 data/                         # User data (on USB partition)
│   ├── 📂 openwebui/               # Open WebUI data
│   ├── 📂 profiles/                # Family profiles
│   ├── 📂 sessions/                # Session logs
│   └── 📂 ollama/models/           # AI models
└── 📄 parent_dashboard.html         # Parent monitoring interface
```

---

## 🛡️ Safety Features

### Automatic Content Filtering
- **K-2 (Ages 5-7)**: Maximum filtering, 50-word responses
- **Elementary (8-10)**: High filtering, 75-word responses  
- **Middle (11-13)**: Moderate filtering, 125-word responses
- **High School (14+)**: Standard filtering, 200-word responses

### Blocked Content
- Violence, inappropriate topics, personal information
- Automatic redirection to safe STEM topics
- All incidents logged for parent review

### Session Monitoring
- Time limits by age group
- Complete conversation history
- Topic tracking and learning metrics
- Safety incident reports

---

## 💻 System Requirements

### Minimum
- Windows 10+ or macOS 10.14+
- 4GB RAM
- 8GB free disk space
- Python 3.9+

### Recommended  
- 8GB+ RAM
- 16GB free disk space
- USB 3.0 drive for portability

---

## 🔧 Configuration

### Environment Variables
Set these before starting for customization:

```bash
# Data location
export DATA_DIR=/path/to/data

# Ollama settings
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODELS=/path/to/models

# Open WebUI settings
export WEBUI_NAME="Sunflower AI"
export WEBUI_AUTH=true
export ENABLE_SIGNUP=false
export PORT=8080
```

### Model Selection
The system auto-selects based on hardware:
- **High-end**: llama3.2:7b
- **Mid-range**: llama3.2:3b  
- **Low-end**: llama3.2:1b
- **Minimum**: llama3.2:1b-q4_0

---

## 📊 Parent Dashboard

Access at: `file:///[DATA_DIR]/parent_dashboard.html`

Features:
- Real-time activity monitoring
- Safety incident alerts
- Learning progress tracking
- Session history and statistics
- Export capabilities

---

## 🚨 Troubleshooting

### Open WebUI won't start
```bash
# Check if port 8080 is in use
netstat -an | grep 8080

# Use alternative port
export PORT=8081
python openwebui_integration.py
```

### Ollama not found
```bash
# Windows: Download from https://ollama.com/download
# macOS: 
brew install ollama
# or
curl -fsSL https://ollama.com/install.sh | sh
```

### Models not loading
```bash
# Manually pull base model
ollama pull llama3.2:3b

# Create Sunflower models
ollama create sunflower-kids -f modelfiles/Sunflower_AI_Kids.modelfile
```

### Permission errors
- Run as Administrator (Windows)
- Check USB drive write permissions
- Ensure data directory is writable

---

## 🔐 Security Best Practices

1. **Save Admin Password**: Generated on first run - store securely
2. **USB Protection**: Keep USB device physically secure
3. **Profile Management**: Regularly review child profiles and settings
4. **Session Reviews**: Check parent dashboard weekly
5. **Safety Alerts**: Respond to any flagged content immediately

---

## 🎯 Quick Commands

### Start Everything
```bash
# One command to rule them all
python openwebui_integration.py
```

### Stop Everything
- Press `Ctrl+C` in terminal
- Or close the launcher window

### Reset System
```bash
# Backup first!
rm -rf data/openwebui
rm -rf data/profiles
python openwebui_integration.py  # Fresh start
```

### Export Data
```python
# In Python
from openwebui_config import OpenWebUIConfig
config = OpenWebUIConfig("./data")
config.export_config("backup.json")
```

---

## 📝 Creating Custom Models

### Basic Template
```modelfile
FROM llama3.2:3b

SYSTEM """
You are Sunflower AI, a safe educational assistant.
Age group: [SPECIFY]
Safety level: [MAXIMUM/HIGH/MODERATE/STANDARD]
Focus: STEM education only
"""

PARAMETER temperature 0.7
PARAMETER max_tokens 150
```

### Apply Custom Model
```bash
ollama create my-custom-model -f my_model.modelfile
```

---

## 🆘 Getting Help

1. **Documentation**: Check `/docs` folder
2. **Logs**: Review `/data/logs` for errors
3. **Parent Dashboard**: Built-in help section
4. **Community**: This is a no-support product - documentation is comprehensive

---

## ✅ Verification Checklist

After setup, verify:
- [ ] Open WebUI loads at http://localhost:8080
- [ ] Admin password saved securely
- [ ] At least one child profile created
- [ ] Parent dashboard accessible
- [ ] Test conversation works
- [ ] Safety filter blocks inappropriate content
- [ ] Sessions are being logged
- [ ] Data persists after restart

---

## 🎉 Success!

You're ready to provide safe, adaptive AI-powered STEM education for your children!

Remember:
- All data stays local on your device
- No internet required after setup
- Complete parental control and monitoring
- Age-appropriate responses guaranteed

**Enjoy your Sunflower AI Education System!** 🌻
