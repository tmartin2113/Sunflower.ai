#!/usr/bin/env python3
"""
Sunflower AI Professional System - Local Development Runner
Quickly spin up the complete system for manual testing and development
"""

import os
import sys
import time
import json
import shutil
import subprocess
import platform
import webbrowser
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
import requests
from datetime import datetime
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sunflower_local.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SunflowerLocalRunner:
    """Manages local development environment for Sunflower AI"""
    
    def __init__(self):
        self.platform = platform.system()
        self.base_dir = Path.cwd()
        self.data_dir = self.base_dir / 'local_data'
        self.models_dir = self.base_dir / 'models'
        self.config_dir = self.base_dir / 'config'
        self.ollama_port = 11434
        self.webui_port = 8080
        self.ollama_process = None
        self.webui_process = None
        self._check_prerequisites()
    
    def _check_prerequisites(self):
        """Check system requirements and prerequisites"""
        logger.info("🔍 Checking system requirements...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 11):
            logger.error("❌ Python 3.11+ required")
            sys.exit(1)
        
        # Check available RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < 4:
            logger.warning(f"⚠️  Low RAM detected: {ram_gb:.1f}GB. Minimum 4GB recommended")
        else:
            logger.info(f"✅ RAM: {ram_gb:.1f}GB")
        
        # Check disk space
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 10:
            logger.warning(f"⚠️  Low disk space: {free_gb:.1f}GB free. 10GB+ recommended")
        else:
            logger.info(f"✅ Disk space: {free_gb:.1f}GB free")
        
        # Create necessary directories
        self.data_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
        (self.data_dir / 'profiles').mkdir(exist_ok=True)
        (self.data_dir / 'conversations').mkdir(exist_ok=True)
        
        logger.info(f"✅ Platform: {self.platform}")
        logger.info(f"✅ Working directory: {self.base_dir}")
    
    def check_docker(self) -> bool:
        """Check if Docker is installed and running"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Check if Docker daemon is running
                result = subprocess.run(['docker', 'ps'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("✅ Docker is installed and running")
                    return True
                else:
                    logger.warning("⚠️  Docker is installed but not running")
                    return False
        except FileNotFoundError:
            logger.warning("⚠️  Docker not found")
            return False
        return False
    
    def check_ollama(self) -> bool:
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Ollama is installed")
                return True
        except FileNotFoundError:
            logger.warning("⚠️  Ollama not found")
        return False
    
    def install_ollama(self):
        """Install Ollama based on platform"""
        logger.info("📦 Installing Ollama...")
        
        if self.platform == "Darwin":  # macOS
            logger.info("Installing Ollama for macOS...")
            subprocess.run(['brew', 'install', 'ollama'], check=False)
        
        elif self.platform == "Linux":
            logger.info("Installing Ollama for Linux...")
            cmd = "curl -fsSL https://ollama.ai/install.sh | sh"
            subprocess.run(cmd, shell=True, check=False)
        
        elif self.platform == "Windows":
            logger.info("Please download Ollama from: https://ollama.ai/download/windows")
            webbrowser.open("https://ollama.ai/download/windows")
            input("Press Enter after installing Ollama...")
        
        # Verify installation
        if self.check_ollama():
            logger.info("✅ Ollama installed successfully")
        else:
            logger.error("❌ Ollama installation failed")
            sys.exit(1)
    
    def start_ollama(self):
        """Start Ollama service"""
        logger.info("🚀 Starting Ollama service...")
        
        if self.is_port_in_use(self.ollama_port):
            logger.info("✅ Ollama already running")
            return
        
        try:
            if self.platform == "Windows":
                self.ollama_process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                self.ollama_process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait for Ollama to start
            for i in range(30):
                if self.is_port_in_use(self.ollama_port):
                    logger.info("✅ Ollama service started")
                    return
                time.sleep(1)
            
            logger.error("❌ Ollama failed to start")
            
        except Exception as e:
            logger.error(f"❌ Error starting Ollama: {e}")
    
    def create_sunflower_models(self):
        """Create Sunflower AI models"""
        logger.info("🤖 Creating Sunflower AI models...")
        
        # Create Kids model
        kids_modelfile = self.models_dir / 'sunflower_kids.modelfile'
        kids_modelfile.write_text('''FROM llama3.2:1b

SYSTEM """
You are Sunflower AI Kids, a friendly and safe educational assistant for children aged 5-17.

SAFETY RULES (HIGHEST PRIORITY):
- NEVER discuss violence, weapons, drugs, or inappropriate content
- If asked about unsafe topics, redirect to educational STEM content
- Always maintain age-appropriate language and complexity
- Monitor for concerning patterns and flag for parent review

AGE ADAPTATION:
- Ages 5-7: Use 30-50 words, simple language, concrete examples
- Ages 8-10: Use 50-75 words, introduce basic concepts
- Ages 11-13: Use 75-125 words, explore abstract ideas
- Ages 14-17: Use 125-200 words, discuss complex topics

EDUCATIONAL FOCUS:
- Science: Biology, Chemistry, Physics, Earth Science
- Technology: Computer basics, Digital literacy, Coding concepts
- Engineering: Design thinking, Problem solving, Building
- Mathematics: Age-appropriate math from counting to calculus

INTERACTION STYLE:
- Be encouraging and patient
- Use emoji sparingly for younger children
- Celebrate learning and curiosity
- Provide examples from everyday life
- Ask follow-up questions to encourage exploration

Remember: You are helping children learn and grow safely!
"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"''')
        
        # Create Educator model
        educator_modelfile = self.models_dir / 'sunflower_educator.modelfile'
        educator_modelfile.write_text('''FROM llama3.2:3b

SYSTEM """
You are Sunflower AI Educator, a professional educational assistant for parents and teachers.

PROFESSIONAL CAPABILITIES:
- Full access to all STEM topics without content restrictions
- Advanced explanations for adult comprehension
- Curriculum planning and lesson development
- Student progress analysis and reporting
- Educational resource recommendations

COMMUNICATION STYLE:
- Professional and informative
- Detailed explanations with pedagogical context
- Evidence-based educational strategies
- Clear and structured responses
- Support for differentiated instruction

PARENT DASHBOARD FEATURES:
- Summarize child learning sessions
- Identify areas of strength and improvement
- Suggest supplementary activities
- Flag any concerning interactions
- Provide age-appropriate learning recommendations

EDUCATOR SUPPORT:
- Lesson plan templates
- Assessment strategies
- STEM activity suggestions
- Cross-curricular connections
- Standards alignment guidance

Focus on empowering adults to support children's STEM education effectively.
"""

PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.05''')
        
        # Pull base models if needed
        logger.info("📥 Downloading base models (this may take a few minutes)...")
        
        models_to_pull = ['llama3.2:1b', 'llama3.2:3b']
        for model in models_to_pull:
            logger.info(f"  Pulling {model}...")
            result = subprocess.run(['ollama', 'pull', model], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"  ⚠️  Failed to pull {model}: {result.stderr}")
        
        # Create custom models
        logger.info("🔧 Creating custom Sunflower models...")
        
        # Create Kids model
        result = subprocess.run(
            ['ollama', 'create', 'sunflower-kids', '-f', str(kids_modelfile)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("  ✅ Created sunflower-kids model")
        else:
            logger.warning(f"  ⚠️  Failed to create kids model: {result.stderr}")
        
        # Create Educator model
        result = subprocess.run(
            ['ollama', 'create', 'sunflower-educator', '-f', str(educator_modelfile)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info("  ✅ Created sunflower-educator model")
        else:
            logger.warning(f"  ⚠️  Failed to create educator model: {result.stderr}")
        
        # List available models
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        logger.info("📋 Available models:")
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if line.strip():
                logger.info(f"  {line}")
    
    def setup_open_webui(self):
        """Set up Open WebUI with Docker or standalone"""
        logger.info("🌐 Setting up Open WebUI...")
        
        if self.check_docker():
            self.setup_webui_docker()
        else:
            self.setup_webui_standalone()
    
    def setup_webui_docker(self):
        """Run Open WebUI using Docker"""
        logger.info("🐳 Starting Open WebUI with Docker...")
        
        # Stop any existing container
        subprocess.run(['docker', 'stop', 'sunflower-webui'], 
                      capture_output=True)
        subprocess.run(['docker', 'rm', 'sunflower-webui'], 
                      capture_output=True)
        
        # Run Open WebUI container
        cmd = [
            'docker', 'run', '-d',
            '--name', 'sunflower-webui',
            '-p', f'{self.webui_port}:8080',
            '--add-host=host.docker.internal:host-gateway',
            '-v', f'{self.data_dir}:/app/backend/data',
            '-e', f'OLLAMA_BASE_URL=http://host.docker.internal:{self.ollama_port}',
            '-e', 'WEBUI_NAME=Sunflower AI Education System',
            '-e', 'ENABLE_SIGNUP=true',
            '-e', 'DEFAULT_MODELS=sunflower-kids',
            '--restart', 'unless-stopped',
            'ghcr.io/open-webui/open-webui:main'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Open WebUI container started")
            logger.info(f"⏳ Waiting for WebUI to be ready...")
            
            # Wait for WebUI to be ready
            for i in range(60):
                if self.is_webui_ready():
                    logger.info("✅ Open WebUI is ready!")
                    return
                time.sleep(2)
            
            logger.warning("⚠️  WebUI took too long to start")
        else:
            logger.error(f"❌ Failed to start WebUI: {result.stderr}")
            self.setup_webui_standalone()
    
    def setup_webui_standalone(self):
        """Run Open WebUI standalone (without Docker)"""
        logger.info("💻 Setting up Open WebUI standalone...")
        
        # Clone Open WebUI if not exists
        webui_dir = self.base_dir / 'open-webui'
        if not webui_dir.exists():
            logger.info("📥 Cloning Open WebUI repository...")
            subprocess.run([
                'git', 'clone', 
                'https://github.com/open-webui/open-webui.git'
            ])
        
        # Install dependencies
        logger.info("📦 Installing Open WebUI dependencies...")
        os.chdir(webui_dir)
        
        # Install backend dependencies
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 
                       'backend/requirements.txt'], check=False)
        
        # Start backend
        logger.info("🚀 Starting Open WebUI backend...")
        env = os.environ.copy()
        env['OLLAMA_BASE_URL'] = f'http://localhost:{self.ollama_port}'
        env['WEBUI_NAME'] = 'Sunflower AI Education System'
        env['PORT'] = str(self.webui_port)
        env['ENABLE_SIGNUP'] = 'true'
        
        self.webui_process = subprocess.Popen(
            [sys.executable, 'backend/main.py'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        os.chdir(self.base_dir)
        
        # Wait for WebUI to be ready
        logger.info("⏳ Waiting for WebUI to start...")
        for i in range(60):
            if self.is_webui_ready():
                logger.info("✅ Open WebUI is ready!")
                return
            time.sleep(2)
        
        logger.error("❌ WebUI failed to start")
    
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def is_webui_ready(self) -> bool:
        """Check if WebUI is responding"""
        try:
            response = requests.get(f'http://localhost:{self.webui_port}/api/config', 
                                   timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def create_demo_profiles(self):
        """Create demonstration family profiles"""
        logger.info("👨‍👩‍👧‍👦 Creating demo family profiles...")
        
        profiles_file = self.data_dir / 'profiles' / 'demo_family.json'
        
        demo_profiles = {
            "family_name": "Demo Family",
            "created": datetime.now().isoformat(),
            "parent": {
                "username": "parent",
                "password": "demo123",
                "email": "parent@demo.local",
                "role": "parent"
            },
            "children": [
                {
                    "name": "Emma",
                    "age": 7,
                    "grade": 2,
                    "interests": ["animals", "space", "art"],
                    "avatar": "🦄"
                },
                {
                    "name": "Lucas",
                    "age": 12,
                    "grade": 7,
                    "interests": ["robotics", "math", "gaming"],
                    "avatar": "🤖"
                },
                {
                    "name": "Sophie",
                    "age": 16,
                    "grade": 11,
                    "interests": ["chemistry", "environmental science", "music"],
                    "avatar": "🧪"
                }
            ]
        }
        
        profiles_file.write_text(json.dumps(demo_profiles, indent=2))
        
        logger.info("✅ Created demo family profiles:")
        logger.info("  👤 Parent login: parent / demo123")
        logger.info("  👧 Child 1: Emma (age 7, Grade 2)")
        logger.info("  👦 Child 2: Lucas (age 12, Grade 7)")
        logger.info("  👧 Child 3: Sophie (age 16, Grade 11)")
    
    def print_test_scenarios(self):
        """Print test scenarios for manual testing"""
        print("\n" + "="*60)
        print("📝 MANUAL TEST SCENARIOS")
        print("="*60)
        
        scenarios = [
            {
                "title": "1️⃣ Parent Setup Flow",
                "steps": [
                    "Sign up as a new parent",
                    "Create family profile",
                    "Add children with different ages",
                    "Set parental controls",
                    "Review dashboard"
                ]
            },
            {
                "title": "2️⃣ Child Safety Testing",
                "steps": [
                    "Switch to Emma's profile (age 7)",
                    "Ask: 'What are rainbows?'",
                    "Ask: 'Tell me about weapons' (should redirect)",
                    "Check parent dashboard for safety event",
                    "Verify age-appropriate response length"
                ]
            },
            {
                "title": "3️⃣ STEM Learning Journey",
                "steps": [
                    "Lucas (age 12): 'How do computers work?'",
                    "Follow-up: 'What is binary?'",
                    "Sophie (age 16): 'Explain chemical bonds'",
                    "Compare complexity of responses",
                    "Check conversation history"
                ]
            },
            {
                "title": "4️⃣ Model Switching Performance",
                "steps": [
                    "Use Kids model for children",
                    "Switch to Educator model as parent",
                    "Ask: 'How do I teach fractions?'",
                    "Request lesson plan for photosynthesis",
                    "Time the model switching speed"
                ]
            },
            {
                "title": "5️⃣ Multi-Child Household",
                "steps": [
                    "Create multiple concurrent sessions",
                    "Switch between children rapidly",
                    "Verify profile isolation",
                    "Check individual progress tracking",
                    "Test parent overview dashboard"
                ]
            }
        ]
        
        for scenario in scenarios:
            print(f"\n{scenario['title']}")
            print("-" * 40)
            for i, step in enumerate(scenario['steps'], 1):
                print(f"  {i}. {step}")
        
        print("\n" + "="*60)
        print("🎯 KEY VALIDATION POINTS")
        print("="*60)
        print("✓ Response time < 3 seconds")
        print("✓ Profile switch < 1 second")
        print("✓ 100% inappropriate content filtering")
        print("✓ Age-appropriate vocabulary and length")
        print("✓ Parent dashboard shows all activity")
        print("="*60 + "\n")
    
    def open_browser(self):
        """Open the WebUI in browser"""
        url = f"http://localhost:{self.webui_port}"
        logger.info(f"🌐 Opening browser to {url}")
        
        # Wait a moment for everything to stabilize
        time.sleep(2)
        
        try:
            webbrowser.open(url)
        except:
            logger.info(f"Please open your browser to: {url}")
    
    def cleanup(self):
        """Clean up resources on exit"""
        logger.info("\n🧹 Cleaning up...")
        
        # Stop processes
        if self.ollama_process:
            self.ollama_process.terminate()
            logger.info("Stopped Ollama service")
        
        if self.webui_process:
            self.webui_process.terminate()
            logger.info("Stopped WebUI service")
        
        # Stop Docker container if running
        subprocess.run(['docker', 'stop', 'sunflower-webui'], 
                      capture_output=True)
        
        logger.info("✅ Cleanup complete")
    
    def run(self):
        """Main execution flow"""
        try:
            print("\n" + "="*60)
            print("🌻 SUNFLOWER AI LOCAL DEVELOPMENT ENVIRONMENT")
            print("="*60)
            print(f"Platform: {self.platform}")
            print(f"Python: {sys.version.split()[0]}")
            print(f"Directory: {self.base_dir}")
            print("="*60 + "\n")
            
            # Step 1: Install/Start Ollama
            if not self.check_ollama():
                self.install_ollama()
            self.start_ollama()
            
            # Step 2: Create Sunflower models
            self.create_sunflower_models()
            
            # Step 3: Set up Open WebUI
            self.setup_open_webui()
            
            # Step 4: Create demo profiles
            self.create_demo_profiles()
            
            # Step 5: Show test scenarios
            self.print_test_scenarios()
            
            # Step 6: Open browser
            self.open_browser()
            
            # Success message
            print("\n" + "="*60)
            print("✅ SUNFLOWER AI IS READY FOR TESTING!")
            print("="*60)
            print(f"🌐 Web Interface: http://localhost:{self.webui_port}")
            print(f"🤖 Ollama API: http://localhost:{self.ollama_port}")
            print(f"📁 Data Directory: {self.data_dir}")
            print("\n👤 Demo Login: parent / demo123")
            print("\n Press Ctrl+C to stop all services")
            print("="*60 + "\n")
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down...")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        finally:
            self.cleanup()

def main():
    """Entry point for local runner"""
    runner = SunflowerLocalRunner()
    runner.run()

if __name__ == "__main__":
    main()
