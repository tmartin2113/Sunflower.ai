#!/usr/bin/env python3
"""
Create all Sunflower AI model variants from base Llama models.
Builds 8 models total: Kids and Educator variants for each base model.
Uses the complete modelfile content from the project.
"""

import os
import sys
import json
import time
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

class ModelCreator:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.modelfiles_dir = self.root_dir / "modelfiles"
        self.staging_dir = self.root_dir / "cdrom_staging" / "models"
        self.temp_models_dir = Path(tempfile.mkdtemp()) / "models"
        
        # Base models to use
        self.base_models = [
            "llama3.2:7b",
            "llama3.2:3b",
            "llama3.2:1b",
            "llama3.2:1b-q4_0"
        ]
        
        # Model variants to create
        self.variants = ["kids", "educator"]
        
        # Ollama configuration
        self.ollama_host = "http://127.0.0.1:11434"
        self.ollama_process = None
        
    def start_ollama(self):
        """Start Ollama server with custom model directory"""
        print("🚀 Starting Ollama server...")
        
        env = os.environ.copy()
        env['OLLAMA_MODELS'] = str(self.temp_models_dir)
        env['OLLAMA_HOST'] = '127.0.0.1:11434'
        
        # Start Ollama serve
        self.ollama_process = subprocess.Popen(
            ['ollama', 'serve'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for Ollama to be ready
        import httpx
        for i in range(30):
            try:
                response = httpx.get(f"{self.ollama_host}/api/version")
                if response.status_code == 200:
                    print("✅ Ollama server ready")
                    return
            except:
                pass
            time.sleep(1)
            
        raise RuntimeError("Failed to start Ollama server")
    
    def stop_ollama(self):
        """Stop Ollama server"""
        if self.ollama_process:
            print("🛑 Stopping Ollama server...")
            self.ollama_process.terminate()
            self.ollama_process.wait()
    
    def pull_base_model(self, model_name):
        """Pull a base model from Ollama"""
        print(f"📥 Pulling {model_name}...")
        
        cmd = ['ollama', 'pull', model_name]
        env = os.environ.copy()
        env['OLLAMA_MODELS'] = str(self.temp_models_dir)
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to pull {model_name}: {result.stderr}")
            raise RuntimeError(f"Failed to pull {model_name}")
            
        print(f"✅ Successfully pulled {model_name}")
    
    def read_modelfile_content(self, variant):
        """Read the complete modelfile content from the project"""
        modelfile_path = self.modelfiles_dir / f"Sunflower_AI_{variant.capitalize()}.modelfile"
        
        if not modelfile_path.exists():
            raise FileNotFoundError(f"Modelfile not found: {modelfile_path}")
            
        with open(modelfile_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def create_modelfile_content(self, variant, base_model):
        """Generate modelfile content for a specific variant and base model"""
        
        # Read the original modelfile
        original_content = self.read_modelfile_content(variant)
        
        # Replace the FROM line with the specific base model
        lines = original_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('FROM'):
                lines[i] = f'FROM {base_model}'
                break
        
        # Return the modified content
        return '\n'.join(lines)
    
    def create_model_variant(self, base_model, variant):
        """Create a model variant using Ollama"""
        model_name = f"sunflower-{variant}-{base_model.split(':')[1]}"
        
        print(f"🔨 Creating {model_name}...")
        
        # Create temporary modelfile with specific base model
        modelfile_content = self.create_modelfile_content(variant, base_model)
        temp_modelfile = self.temp_models_dir / f"{model_name}.modelfile"
        
        with open(temp_modelfile, "w", encoding='utf-8') as f:
            f.write(modelfile_content)
        
        # Create model using Ollama
        cmd = ['ollama', 'create', model_name, '-f', str(temp_modelfile)]
        env = os.environ.copy()
        env['OLLAMA_MODELS'] = str(self.temp_models_dir)
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to create {model_name}: {result.stderr}")
            raise RuntimeError(f"Failed to create {model_name}")
            
        print(f"✅ Successfully created {model_name}")
        
        # Clean up temporary modelfile
        temp_modelfile.unlink()
        
        return model_name
    
    def verify_model(self, model_name):
        """Verify a model works correctly"""
        print(f"🔍 Verifying {model_name}...")
        
        import httpx
        
        # Test the model with a simple prompt appropriate for the model type
        if "kids" in model_name:
            test_prompt = "I'm 8 years old. What makes rainbows?"
        else:
            test_prompt = "What strategies can I use to teach fractions to 4th graders?"
        
        response = httpx.post(
            f"{self.ollama_host}/api/generate",
            json={
                "model": model_name,
                "prompt": test_prompt,
                "stream": False
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            if "response" in result:
                print(f"✅ {model_name} verified - Response: {result['response'][:50]}...")
                return True
                
        print(f"❌ {model_name} verification failed")
        return False
    
    def copy_models_to_staging(self):
        """Copy all models to staging directory"""
        print("📦 Copying models to staging...")
        
        # Create staging directory
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy entire Ollama models directory
        source_models = self.temp_models_dir
        dest_models = self.staging_dir / ".ollama"
        
        if dest_models.exists():
            shutil.rmtree(dest_models)
            
        shutil.copytree(source_models, dest_models)
        
        print(f"✅ Models copied to {dest_models}")
        
        # Copy original modelfiles for reference
        modelfiles_dest = self.staging_dir / "modelfiles"
        modelfiles_dest.mkdir(exist_ok=True)
        
        for variant in self.variants:
            src_modelfile = self.modelfiles_dir / f"Sunflower_AI_{variant.capitalize()}.modelfile"
            if src_modelfile.exists():
                shutil.copy2(src_modelfile, modelfiles_dest)
        
        # Create model manifest
        manifest = {
            "build_date": datetime.now().isoformat(),
            "base_models": self.base_models,
            "variants": self.variants,
            "total_models": len(self.base_models) * len(self.variants),
            "models": []
        }
        
        # List all created models
        for base in self.base_models:
            for variant in self.variants:
                model_name = f"sunflower-{variant}-{base.split(':')[1]}"
                manifest["models"].append({
                    "name": model_name,
                    "base": base,
                    "variant": variant,
                    "description": f"Sunflower AI {variant.capitalize()} model based on {base}"
                })
        
        with open(self.staging_dir / "model_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
    
    def calculate_model_sizes(self):
        """Calculate and report model sizes"""
        print("\n📊 Model Size Report:")
        print("-" * 50)
        
        total_size = 0
        model_sizes = {}
        
        for root, dirs, files in os.walk(self.staging_dir):
            for file in files:
                file_path = Path(root) / file
                size = file_path.stat().st_size
                total_size += size
                
                if size > 100 * 1024 * 1024:  # Show files > 100MB
                    size_gb = size / (1024 ** 3)
                    model_sizes[file] = size_gb
                    print(f"{file}: {size_gb:.2f} GB")
        
        total_gb = total_size / (1024 ** 3)
        print("-" * 50)
        print(f"Total size: {total_gb:.2f} GB")
        
        return total_gb, model_sizes
    
    def validate_modelfiles_exist(self):
        """Ensure required modelfiles exist before starting"""
        print("📋 Validating modelfiles...")
        
        missing_files = []
        for variant in self.variants:
            modelfile_path = self.modelfiles_dir / f"Sunflower_AI_{variant.capitalize()}.modelfile"
            if not modelfile_path.exists():
                missing_files.append(str(modelfile_path))
        
        if missing_files:
            print("❌ Missing required modelfiles:")
            for file in missing_files:
                print(f"   - {file}")
            raise FileNotFoundError("Please ensure all modelfiles are present in the modelfiles directory")
        
        print("✅ All required modelfiles found")
    
    def build(self):
        """Execute full model creation process"""
        print(f"🌻 Sunflower AI Model Creation System")
        print(f"📅 Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📦 Creating {len(self.base_models) * len(self.variants)} model variants")
        print("-" * 50)
        
        try:
            # Validate modelfiles exist
            self.validate_modelfiles_exist()
            
            # Ensure Ollama is installed
            if shutil.which('ollama') is None:
                print("❌ Ollama not found. Please install Ollama first.")
                print("   Visit: https://ollama.ai")
                sys.exit(1)
            
            # Start Ollama with custom model directory
            self.start_ollama()
            
            # Pull all base models
            print("\n📥 Downloading base models...")
            for model in self.base_models:
                self.pull_base_model(model)
            
            # Create all variants
            print("\n🔨 Creating model variants...")
            created_models = []
            
            for base_model in self.base_models:
                for variant in self.variants:
                    model_name = self.create_model_variant(base_model, variant)
                    
                    # Verify the model works
                    if self.verify_model(model_name):
                        created_models.append(model_name)
                    else:
                        print(f"⚠️ Skipping {model_name} due to verification failure")
            
            # Copy to staging
            self.copy_models_to_staging()
            
            # Report sizes
            total_size, model_sizes = self.calculate_model_sizes()
            
            print(f"\n✅ Model creation completed successfully!")
            print(f"📁 Created {len(created_models)} models")
            print(f"💾 Total size: {total_size:.2f} GB")
            print(f"📍 Location: {self.staging_dir}")
            
            # Check if size fits on target USB
            if total_size > 8.0:
                print(f"\n⚠️ WARNING: Total model size ({total_size:.2f} GB) exceeds 8GB!")
                print("   Consider using 16GB USB drives for distribution")
            
            # Save build record
            build_record = {
                "build_date": datetime.now().isoformat(),
                "models_created": created_models,
                "total_size_gb": total_size,
                "model_sizes": model_sizes,
                "output_path": str(self.staging_dir),
                "success": True
            }
            
            records_dir = self.root_dir / "manufacturing" / "batch_records"
            records_dir.mkdir(parents=True, exist_ok=True)
            
            with open(records_dir / f"models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                json.dump(build_record, f, indent=2)
                
        except Exception as e:
            print(f"\n❌ Model creation failed: {e}")
            raise
        finally:
            self.stop_ollama()
            
            # Optionally clean up temp directory
            if input("\n🗑️ Delete temporary files? (y/n): ").lower() == 'y':
                shutil.rmtree(self.temp_models_dir.parent, ignore_errors=True)
                print("✅ Temporary files cleaned up")


if __name__ == "__main__":
    creator = ModelCreator()
    creator.build()
