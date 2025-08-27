# Troubleshooting Guide

## Quick Fixes (Try These First!)

Before diving into detailed troubleshooting, try these quick solutions that resolve 90% of issues:

1. **Restart the Application** - Close Sunflower AI completely and restart
2. **Check USB Connection** - Ensure USB device is fully inserted
3. **Try Different USB Port** - Preferably a USB 3.0 port (blue)
4. **Restart Computer** - Resolves many temporary issues
5. **Run as Administrator** (Windows) or with **sudo** (Mac)

## Common Issues and Solutions

### 🚫 Sunflower AI Won't Start

#### Symptoms
- Nothing happens when clicking launcher
- Error message appears immediately
- Application starts but closes instantly

#### Solutions

**Windows:**
```batch
1. Right-click START_SUNFLOWER.bat
2. Select "Run as Administrator"
3. If User Account Control appears, click "Yes"

If still not working:
1. Open Command Prompt as Administrator
2. Navigate to USB drive: 
   cd /d E:\  (replace E: with your USB drive letter)
3. Run: START_SUNFLOWER.bat
4. Note any error messages
```

**macOS:**
```bash
1. Open Terminal
2. Navigate to USB drive:
   cd /Volumes/SUNFLOWER_AI
3. Run: sudo ./START_SUNFLOWER.command
4. Enter your Mac password
5. Note any error messages
```

### ⚠️ "Python Not Found" Error

#### Windows Solution
```batch
# Option 1: Install Python from USB
1. Navigate to USB drive
2. Open installers folder
3. Run python-3.9.exe
4. CHECK "Add Python to PATH"
5. Complete installation
6. Restart Sunflower AI

# Option 2: Download Python
1. Visit python.org
2. Download Python 3.9 or newer
3. Install with "Add to PATH" checked
```

#### macOS Solution
```bash
# Check if Python is installed
python3 --version

# If not installed:
# Option 1: Install from USB
cd /Volumes/SUNFLOWER_AI/installers
sudo installer -pkg python-3.9.pkg -target /

# Option 2: Install via Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.9
```

### 🐌 Slow Response Times

#### Diagnosis Checklist
- [ ] Check available RAM (need 4GB minimum)
- [ ] Close unnecessary programs
- [ ] Verify USB 3.0 connection (not 2.0)
- [ ] Check CPU usage (should be <80%)
- [ ] Confirm correct model loaded

#### Solutions by Cause

**Low Memory:**
```
1. Close all browsers except Sunflower AI
2. Close background applications
3. Check Task Manager/Activity Monitor
4. Free up at least 2GB RAM
5. Consider memory upgrade if persistent
```

**Wrong Model Size:**
```python
# Force smaller model for low-spec systems
1. Open Parent Dashboard
2. Settings → Advanced
3. Model Selection → Choose smaller model:
   - 7B model: Needs 8GB+ RAM
   - 3B model: Needs 4GB+ RAM  
   - 1B model: Needs 2GB+ RAM
4. Restart application
```

**USB 2.0 Connection:**
```
USB Port Identification:
- USB 2.0: Black or white port
- USB 3.0: Blue port
- USB 3.1: Teal port
- USB-C: Oval shaped

Always use USB 3.0 or higher!
```

### 🔒 "Access Denied" Errors

#### Windows Specific
```
Solutions:
1. Disable antivirus temporarily
2. Add Sunflower AI to exceptions:
   - Windows Defender → Add exclusion
   - Add USB drive path
3. Check folder permissions:
   - Right-click USB drive
   - Properties → Security
   - Ensure "Full Control"
4. Run in compatibility mode:
   - Right-click launcher
   - Properties → Compatibility
   - Run as Windows 8
```

#### macOS Specific
```bash
# Fix permissions
sudo chmod +x /Volumes/SUNFLOWER_AI/START_SUNFLOWER.command

# Grant full disk access:
1. System Preferences → Security & Privacy
2. Privacy tab → Full Disk Access
3. Add Terminal and Sunflower AI

# If Gatekeeper blocks:
sudo spctl --master-disable
# Run Sunflower AI
sudo spctl --master-enable
```

### 👤 Profile Issues

#### "Profile Won't Load"
```
1. Check USB space:
   - Need 100MB free per profile
   - Delete old conversations if full

2. Verify profile integrity:
   - Parent Dashboard → Profiles
   - Select problem profile
   - Click "Verify Integrity"
   - Repair if corrupted

3. Reset profile:
   - Export conversation history first
   - Delete profile
   - Recreate with same settings
   - Import history if desired
```

#### "Can't Create New Profile"
```
Check these limits:
- Maximum 8 profiles per device
- 50MB available space needed
- Parent password required
- Valid age range: 5-17
```

### 🌐 "Ollama Service Not Found"

#### Reinstall Ollama Service
```batch
Windows:
1. Open Services (services.msc)
2. Look for "Ollama Service"
3. If missing, reinstall:
   cd E:\installers
   ollama-windows-amd64.exe /S
4. Start service:
   net start ollama

macOS:
1. Check if running:
   ps aux | grep ollama
2. If not, reinstall:
   cd /Volumes/SUNFLOWER_AI/installers
   ./install-ollama.sh
3. Start service:
   ollama serve
```

#### Load Models Manually
```bash
# If models aren't loading automatically
ollama list  # Check available models

# Load required models
ollama run sunflower-kids
ollama run sunflower-educator

# Verify loaded
ollama list  # Should show both models
```

### 🖥️ Interface Issues

#### "Blank Screen" or "Page Won't Load"

```
1. Check if services are running:
   - Ollama service: http://localhost:11434
   - Open WebUI: http://localhost:8080

2. Clear browser cache:
   - Ctrl+Shift+Delete (Windows)
   - Cmd+Shift+Delete (Mac)
   - Clear last hour

3. Try different browser:
   - Chrome (recommended)
   - Firefox
   - Edge
   - Safari (Mac)

4. Check firewall:
   - Allow localhost connections
   - Ports 8080 and 11434
```

#### "Cannot Connect to Server"
```python
# Restart services manually
1. Stop all services:
   - Close Sunflower AI
   - Stop Ollama: ollama stop
   
2. Start in order:
   - Start Ollama: ollama serve
   - Wait 10 seconds
   - Start Sunflower AI
   
3. Verify connections:
   - Visit: http://localhost:11434
   - Should see: "Ollama is running"
   - Visit: http://localhost:8080
   - Should see: Login page
```

### 💾 Storage Issues

#### "USB Drive Full"
```
Space Usage Breakdown:
- System files: 4GB (CD-ROM partition)
- Models: 2-4GB
- Profiles: 50MB each
- History: 10MB per 100 conversations

Cleanup Options:
1. Clear old conversations:
   Parent Dashboard → Maintenance → Clear History
   
2. Export and archive:
   Parent Dashboard → Export Data → Archive to Computer
   
3. Remove unused profiles:
   Parent Dashboard → Profiles → Delete Unused
```

#### "Cannot Write to USB"
```
Check these:
1. USB not write-protected:
   - No physical lock switch
   - Not set read-only in OS
   
2. Fix permissions:
   Windows: 
   - Properties → Security → Edit
   - Give Full Control to Users
   
   macOS:
   - Get Info → Sharing & Permissions
   - Set to Read & Write
   
3. USB health:
   - Run disk check
   - Consider replacement if failing
```

## Platform-Specific Issues

### Windows-Specific

#### Windows Defender Blocking
```
1. Open Windows Security
2. Virus & threat protection
3. Protection history
4. Find Sunflower AI entries
5. Allow on device
6. Add exclusion:
   - Settings → Exclusions
   - Add folder → Select USB drive
```

#### PowerShell Execution Policy
```powershell
# If scripts won't run
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verify
Get-ExecutionPolicy

# Should show: RemoteSigned
```

### macOS-Specific

#### "Application Can't Be Opened"
```bash
# Remove quarantine flag
xattr -d com.apple.quarantine /Volumes/SUNFLOWER_AI/START_SUNFLOWER.command

# If app is from unidentified developer
System Preferences → Security & Privacy → General
Click "Open Anyway" after trying to run
```

#### macOS Ventura/Sonoma Issues
```
New security requirements:
1. System Settings → Privacy & Security
2. Developer Tools → Terminal (enable)
3. Full Disk Access → Add Sunflower AI
4. Input Monitoring → Add if using voice
```

## Error Messages Explained

### Common Error Codes

| Error Code | Meaning | Solution |
|------------|---------|----------|
| ERR_001 | Python not found | Install Python 3.9+ |
| ERR_002 | Ollama not running | Start Ollama service |
| ERR_003 | Model not loaded | Run model loader |
| ERR_004 | Port in use | Change port or find conflicting app |
| ERR_005 | Insufficient memory | Close programs or upgrade RAM |
| ERR_006 | USB not detected | Reconnect USB device |
| ERR_007 | Profile corrupted | Restore from backup |
| ERR_008 | Permission denied | Run as administrator |
| ERR_009 | Network error | Check firewall settings |
| ERR_010 | Version mismatch | Reinstall application |

## Performance Optimization

### Speed Up Response Times

```
1. Optimal Model Selection:
   - 16GB RAM: Use 7B model
   - 8GB RAM: Use 3B model
   - 4GB RAM: Use 1B model
   
2. System Optimization:
   - Disable Windows animations
   - Close background apps
   - Use SSD if available
   - Keep 20% disk space free
   
3. Browser Settings:
   - Disable extensions
   - Use hardware acceleration
   - Clear cache regularly
```

### Reduce Memory Usage

```python
# Memory Management Settings
Parent Dashboard → Advanced → Performance

Options:
- Reduce context window: 2048 → 1024
- Clear cache on exit: Enable
- Limit conversation history: 100 messages
- Compress old conversations: Enable
```

## Diagnostic Tools

### Built-in Diagnostics

```
Parent Dashboard → Support → Diagnostics

Run these tests:
1. System Requirements Check
2. Service Health Check  
3. Model Integrity Test
4. Profile Validation
5. Performance Benchmark

Export results for support
```

### Manual Diagnostics

```bash
# Check system resources
Windows: resmon.exe
macOS: Activity Monitor

# Check services
netstat -an | grep 8080  # WebUI port
netstat -an | grep 11434 # Ollama port

# Check logs
USB_Drive/logs/system.log
USB_Drive/logs/error.log
```

## When to Contact Support

### Collect This Information First

```
Required Information:
1. Error messages (exact text or screenshot)
2. System specs (OS, RAM, CPU)
3. USB device model
4. Steps to reproduce issue
5. Diagnostic report (from Parent Dashboard)
```

### Support Channels

**Self-Service:**
- This documentation
- Video tutorials on USB device
- Community forum

**Direct Support:**
- Email: support@sunflower-ai.com
- Include diagnostic report
- Response within 48 hours

## Prevention Tips

### Regular Maintenance

**Weekly:**
- Clear browser cache
- Review error logs
- Check available space
- Update profiles

**Monthly:**
- Export conversation history
- Clean USB contacts
- Check for OS updates
- Review security settings

### Best Practices

1. **Always eject USB safely** before removing
2. **Use USB 3.0 ports** for best performance
3. **Keep 1GB free space** on USB partition
4. **Regular backups** of profiles and history
5. **Don't modify system files** on CD-ROM partition

---

*Most issues can be resolved with the solutions above. If problems persist after trying these steps, contact support with diagnostic information.*
