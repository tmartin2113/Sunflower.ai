"""
Ollama integration manager
Handles starting, stopping, and communicating with Ollama
"""

import os
import sys
import time
import subprocess
import platform
import httpx
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, List
import logging

from constants import OLLAMA_HOST, OLLAMA_TIMEOUT, OLLAMA_ENDPOINTS


class OllamaManager:
    """Manages Ollama lifecycle and communications"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.process = None
        self.client = httpx.Client(timeout=OLLAMA_TIMEOUT) # Sync client
        self.async_client = httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) # Async client
        self.is_running = False
        self.using_existing = False
        
    def check_existing_ollama(self) -> Dict:
        """Check if Ollama is already running"""
        try:
            response = httpx.get(f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['version']}", timeout=2)
            if response.status_code == 200:
                version_info = response.json()
                self.logger.info(f"Found existing Ollama: {version_info}")
                return {
                    'installed': True,
                    'running': True,
                    'version': version_info.get('version', 'unknown')
                }
        except:
            pass
        
        # Check if installed but not running
        if platform.system() == "Windows":
            ollama_cmd = "ollama.exe"
        else:
            ollama_cmd = "ollama"
            
        if subprocess.run(["which", ollama_cmd], capture_output=True).returncode == 0:
            return {
                'installed': True,
                'running': False,
                'path': subprocess.run(["which", ollama_cmd], capture_output=True, text=True).stdout.strip()
            }
        
        return {'installed': False}
    
    def start(self) -> bool:
        """Start Ollama server"""
        existing = self.check_existing_ollama()
        
        if existing.get('running'):
            self.logger.info("Using existing Ollama instance")
            self.using_existing = True
            self.is_running = True
            return True
        
        # Start our bundled Ollama
        ollama_path = self.config.ollama_path
        
        if not ollama_path.exists():
            self.logger.error(f"Ollama not found at {ollama_path}")
            return False
        
        # Set environment for model storage
        env = os.environ.copy()
        env['OLLAMA_MODELS'] = str(self.config.models_path / ".ollama")
        env['OLLAMA_HOST'] = '127.0.0.1:11434'
        
        # Start Ollama
        try:
            if platform.system() == "Windows":
                # Windows: Hide console window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                self.process = subprocess.Popen(
                    [str(ollama_path), "serve"],
                    env=env,
                    startupinfo=startupinfo,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # macOS/Linux
                self.process = subprocess.Popen(
                    [str(ollama_path), "serve"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Wait for server to be ready
            for i in range(30):
                try:
                    response = httpx.get(f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['version']}", timeout=1)
                    if response.status_code == 200:
                        self.logger.info("Ollama server started successfully")
                        self.is_running = True
                        return True
                except:
                    pass
                time.sleep(1)
            
            self.logger.error("Ollama server failed to start")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start Ollama: {e}")
            return False
    
    def stop(self):
        """Stop Ollama server"""
        if self.using_existing:
            self.logger.info("Not stopping existing Ollama instance")
            return
        
        if self.process:
            self.logger.info("Stopping Ollama server")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        
        self.is_running = False
    
    def list_models_sync(self) -> List[Dict]:
        """List available models synchronously."""
        try:
            response = self.client.get(f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['tags']}")
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
        except Exception as e:
            self.logger.error(f"Failed to list models synchronously: {e}")
        return []

    async def list_models(self) -> List[Dict]:
        """List available models"""
        try:
            response = await self.async_client.get(f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['tags']}")
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
        
        return []
    
    async def pull_model(self, model_name: str, progress_callback=None):
        """Pull a model from Ollama registry"""
        try:
            async with self.async_client.stream(
                'POST',
                f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['pull']}",
                json={'name': model_name}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if progress_callback:
                            progress_callback(data)
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            raise
    
    async def generate(self, model: str, prompt: str, system: str = None, 
                      temperature: float = 0.7, stream: bool = True):
        """Generate response from model"""
        payload = {
            'model': model,
            'prompt': prompt,
            'temperature': temperature,
            'stream': stream
        }
        
        if system is not None:
            payload['system'] = system
        
        if stream:
            # The ModelManager uses the synchronous, streaming version.
            try:
                with self.client.stream(
                    'POST',
                    f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['generate']}",
                    json=payload
                ) as response:
                    for line in response.iter_lines():
                        if line:
                            yield json.loads(line)
            except httpx.ConnectError as e:
                self.logger.error(f"Connection to Ollama failed: {e}. Is Ollama running?")
                # Yield an error message that can be displayed to the user
                yield {"error": "Could not connect to the AI engine. Please ensure it is running."}
            except Exception as e:
                self.logger.error(f"Error in streaming generation: {e}")
                yield {"error": "An unexpected error occurred while generating the response."}
        else:
            # Async, non-streaming path
            response = await self.async_client.post(
                f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['generate']}",
                json=payload
            )
            yield response.json()
    
    async def chat(self, model: str, messages: List[Dict], stream: bool = True):
        """Chat with model using conversation history"""
        payload = {
            'model': model,
            'messages': messages,
            'stream': stream
        }
        
        if stream:
            async with self.async_client.stream(
                'POST',
                f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['chat']}",
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)
        else:
            response = await self.async_client.post(
                f"{OLLAMA_HOST}{OLLAMA_ENDPOINTS['chat']}",
                json=payload
            )
            yield response.json()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()
        if hasattr(self, 'client'):
            self.client.close()
        if hasattr(self, 'async_client'):
            asyncio.create_task(self.async_client.aclose())
