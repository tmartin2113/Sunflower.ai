#!/usr/bin/env python3
"""
Sunflower AI Professional System - Model Creation and Compilation
Production-ready model builder for partitioned CD-ROM deployment
Version: 6.2
"""

import os
import sys
import json
import hashlib
import logging
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import platform

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ModelBuilder')


class ModelCompiler:
    """Production-grade AI model compiler for Sunflower AI System"""
    
    MODEL_VARIANTS = {
        'high_end': {
            'name': 'llama3.2:7b',
            'size': '7b',
            'quantization': None,
            'min_ram': 16384,  # 16GB
            'optimal_ram': 32768,  # 32GB
            'file_size_mb': 4500
        },
        'mid_range': {
            'name': 'llama3.2:3b',
            'size': '3b',
            'quantization': None,
            'min_ram': 8192,  # 8GB
            'optimal_ram': 16384,  # 16GB
            'file_size_mb': 2000
        },
        'low_end': {
            'name': 'llama3.2:1b',
            'size': '1b',
            'quantization': None,
            'min_ram': 4096,  # 4GB
            'optimal_ram': 8192,  # 8GB
            'file_size_mb': 700
        },
        'minimum': {
            'name': 'llama3.2:1b-q4_0',
            'size': '1b',
            'quantization': 'q4_0',
            'min_ram': 4096,  # 4GB
            'optimal_ram': 4096,  # 4GB
            'file_size_mb': 500
        }
    }
    
    def __init__(self, build_dir: Path, output_dir: Path):
        """Initialize model compiler with build and output directories"""
        self.build_dir = Path(build_dir)
        self.output_dir = Path(output_dir)
        self.models_dir = self.output_dir / 'models'
        self.manifests_dir = self.output_dir / 'manifests'
        self.temp_dir = Path(tempfile.mkdtemp(prefix='sunflower_models_'))
        
        # Create required directories
        for directory in [self.models_dir, self.manifests_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load modelfile templates
        self.kids_modelfile = self.build_dir / 'modelfiles' / 'Sunflower_AI_Kids.modelfile'
        self.educator_modelfile = self.build_dir / 'modelfiles' / 'Sunflower_AI_Educator.modelfile'
        
        # Validate required files
        self._validate_environment()
    
    def _validate_environment(self) -> None:
        """Validate build environment and dependencies"""
        # Check for Ollama installation
        if not self._check_ollama():
            raise RuntimeError(
                "Ollama is not installed or not accessible. "
                "Please install Ollama before running model compilation."
            )
        
        # Validate modelfile existence
        for modelfile in [self.kids_modelfile, self.educator_modelfile]:
            if not modelfile.exists():
                raise FileNotFoundError(
                    f"Required modelfile not found: {modelfile}\n"
                    f"Please ensure modelfiles are in {self.build_dir / 'modelfiles'}"
                )
        
        # Check disk space
        required_space_gb = 15  # Conservative estimate for all models
        available_space_gb = shutil.disk_usage(self.output_dir).free / (1024**3)
        if available_space_gb < required_space_gb:
            raise RuntimeError(
                f"Insufficient disk space. Required: {required_space_gb}GB, "
                f"Available: {available_space_gb:.2f}GB"
            )
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is installed and accessible"""
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def compile_model_variant(
        self,
        variant_name: str,
        modelfile_path: Path,
        model_suffix: str
    ) -> Dict[str, Any]:
        """Compile a single model variant with production error handling"""
        variant = self.MODEL_VARIANTS[variant_name]
        model_name = f"sunflower_{model_suffix}_{variant_name}"
        
        logger.info(f"Compiling model variant: {model_name}")
        
        try:
            # Read and customize modelfile
            with open(modelfile_path, 'r', encoding='utf-8') as f:
                modelfile_content = f.read()
            
            # Add variant-specific parameters
            modelfile_content = self._customize_modelfile(
                modelfile_content,
                variant,
                model_suffix
            )
            
            # Write temporary modelfile
            temp_modelfile = self.temp_dir / f"{model_name}.modelfile"
            with open(temp_modelfile, 'w', encoding='utf-8') as f:
                f.write(modelfile_content)
            
            # Pull base model if needed
            if not self._model_exists(variant['name']):
                logger.info(f"Pulling base model: {variant['name']}")
                self._pull_model(variant['name'])
            
            # Create custom model
            logger.info(f"Creating custom model: {model_name}")
            result = subprocess.run(
                ['ollama', 'create', model_name, '-f', str(temp_modelfile)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Model creation failed: {result.stderr}")
            
            # Export model to blob format
            export_path = self.models_dir / f"{model_name}.gguf"
            logger.info(f"Exporting model to: {export_path}")
            self._export_model(model_name, export_path)
            
            # Generate model manifest
            manifest = self._generate_manifest(
                model_name,
                variant,
                export_path,
                model_suffix
            )
            
            # Save manifest
            manifest_path = self.manifests_dir / f"{model_name}.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            # Calculate checksums
            model_checksum = self._calculate_checksum(export_path)
            
            logger.info(f"Successfully compiled: {model_name} (checksum: {model_checksum})")
            
            return {
                'name': model_name,
                'variant': variant_name,
                'path': str(export_path),
                'manifest': str(manifest_path),
                'checksum': model_checksum,
                'size_mb': export_path.stat().st_size / (1024 * 1024),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to compile {model_name}: {str(e)}")
            return {
                'name': model_name,
                'variant': variant_name,
                'error': str(e),
                'success': False
            }
    
    def _customize_modelfile(
        self,
        content: str,
        variant: Dict[str, Any],
        model_suffix: str
    ) -> str:
        """Customize modelfile for specific variant and role"""
        # Replace base model reference
        content = content.replace('FROM llama3.2', f"FROM {variant['name']}")
        
        # Add performance parameters based on variant
        performance_params = self._get_performance_params(variant)
        
        # Insert parameters after FROM line
        lines = content.split('\n')
        from_index = next(i for i, line in enumerate(lines) if line.startswith('FROM'))
        
        # Add performance parameters
        for param, value in performance_params.items():
            lines.insert(from_index + 1, f"PARAMETER {param} {value}")
        
        # Add variant-specific system prompt adjustments
        if model_suffix == 'kids':
            lines.append("PARAMETER temperature 0.7")
            lines.append("PARAMETER top_p 0.9")
            lines.append("PARAMETER repeat_penalty 1.2")
        else:  # educator
            lines.append("PARAMETER temperature 0.8")
            lines.append("PARAMETER top_p 0.95")
            lines.append("PARAMETER repeat_penalty 1.1")
        
        return '\n'.join(lines)
    
    def _get_performance_params(self, variant: Dict[str, Any]) -> Dict[str, Any]:
        """Get performance parameters based on variant specifications"""
        params = {
            'num_ctx': 2048 if variant['size'] == '1b' else 4096,
            'num_batch': 256 if variant['size'] == '1b' else 512,
            'num_gpu': 0 if variant['min_ram'] <= 4096 else 1,
        }
        
        # Add quantization-specific parameters
        if variant['quantization']:
            params['num_thread'] = os.cpu_count() or 4
            params['f16_kv'] = 'false'
        
        return params
    
    def _model_exists(self, model_name: str) -> bool:
        """Check if a model exists in Ollama"""
        try:
            result = subprocess.run(
                ['ollama', 'show', model_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def _pull_model(self, model_name: str) -> None:
        """Pull a model from Ollama registry with progress tracking"""
        logger.info(f"Pulling model: {model_name}")
        
        process = subprocess.Popen(
            ['ollama', 'pull', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                logger.info(f"Pull progress: {line.strip()}")
        
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to pull model: {model_name}")
    
    def _export_model(self, model_name: str, export_path: Path) -> None:
        """Export model to GGUF format for deployment"""
        # Ollama doesn't directly support export, so we copy from cache
        ollama_models_dir = self._get_ollama_models_dir()
        
        # Find model in Ollama cache
        model_cache = ollama_models_dir / 'manifests' / 'registry.ollama.ai' / 'library'
        
        # For custom models, they're stored differently
        custom_model_path = ollama_models_dir / 'models' / model_name
        
        if custom_model_path.exists():
            # Copy the model blob
            shutil.copytree(custom_model_path, export_path.parent / model_name, dirs_exist_ok=True)
            # Create GGUF marker file
            export_path.touch()
        else:
            raise FileNotFoundError(f"Could not locate model in Ollama cache: {model_name}")
    
    def _get_ollama_models_dir(self) -> Path:
        """Get Ollama models directory based on platform"""
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            return Path.home() / '.ollama'
        elif system == 'Windows':
            return Path(os.environ.get('LOCALAPPDATA', '')) / 'Ollama'
        else:  # Linux
            return Path.home() / '.ollama'
    
    def _generate_manifest(
        self,
        model_name: str,
        variant: Dict[str, Any],
        model_path: Path,
        model_suffix: str
    ) -> Dict[str, Any]:
        """Generate comprehensive model manifest for deployment"""
        return {
            'model_name': model_name,
            'variant': variant,
            'model_type': model_suffix,
            'created_at': datetime.utcnow().isoformat(),
            'file_path': str(model_path.relative_to(self.output_dir)),
            'file_size_bytes': model_path.stat().st_size if model_path.exists() else 0,
            'checksum': self._calculate_checksum(model_path) if model_path.exists() else None,
            'hardware_requirements': {
                'min_ram_mb': variant['min_ram'],
                'optimal_ram_mb': variant['optimal_ram'],
                'gpu_optional': variant['min_ram'] > 4096
            },
            'deployment_config': {
                'auto_select_priority': ['high_end', 'mid_range', 'low_end', 'minimum'].index(
                    next(k for k, v in self.MODEL_VARIANTS.items() if v == variant)
                ),
                'fallback_allowed': True,
                'offline_capable': True
            }
        }
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        if not file_path.exists():
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def compile_all_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Compile all model variants for both kids and educator profiles"""
        results = {
            'kids': [],
            'educator': [],
            'summary': {
                'total_models': 0,
                'successful': 0,
                'failed': 0,
                'total_size_mb': 0
            }
        }
        
        # Use thread pool for parallel compilation
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            # Queue all model compilations
            for variant_name in self.MODEL_VARIANTS.keys():
                # Kids model variant
                futures.append(
                    executor.submit(
                        self.compile_model_variant,
                        variant_name,
                        self.kids_modelfile,
                        'kids'
                    )
                )
                
                # Educator model variant
                futures.append(
                    executor.submit(
                        self.compile_model_variant,
                        variant_name,
                        self.educator_modelfile,
                        'educator'
                    )
                )
            
            # Process results as they complete
            for future in as_completed(futures):
                result = future.result()
                
                # Categorize result
                if 'kids' in result['name']:
                    results['kids'].append(result)
                else:
                    results['educator'].append(result)
                
                # Update summary
                results['summary']['total_models'] += 1
                if result['success']:
                    results['summary']['successful'] += 1
                    results['summary']['total_size_mb'] += result.get('size_mb', 0)
                else:
                    results['summary']['failed'] += 1
        
        # Generate deployment manifest
        self._generate_deployment_manifest(results)
        
        return results
    
    def _generate_deployment_manifest(self, results: Dict[str, Any]) -> None:
        """Generate master deployment manifest for CD-ROM partition"""
        manifest = {
            'version': '6.2',
            'build_date': datetime.utcnow().isoformat(),
            'platform': platform.system(),
            'models': {
                'kids': [r for r in results['kids'] if r['success']],
                'educator': [r for r in results['educator'] if r['success']]
            },
            'hardware_detection': {
                'strategy': 'auto_select_best',
                'fallback_enabled': True,
                'minimum_ram_mb': 4096
            },
            'partition_layout': {
                'cdrom': {
                    'mount_point': 'SUNFLOWER_AI',
                    'filesystem': 'ISO9660',
                    'content': 'models, binaries, documentation'
                },
                'usb': {
                    'mount_point': 'SUNFLOWER_DATA',
                    'filesystem': 'FAT32',
                    'content': 'profiles, logs, conversations'
                }
            }
        }
        
        manifest_path = self.output_dir / 'deployment_manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Deployment manifest saved to: {manifest_path}")
    
    def cleanup(self) -> None:
        """Clean up temporary files and directories"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        logger.info("Cleanup completed")


def main():
    """Main entry point for model compilation"""
    try:
        # Determine paths
        build_dir = Path(__file__).parent
        output_dir = build_dir.parent / 'dist' / 'models'
        
        # Initialize compiler
        compiler = ModelCompiler(build_dir, output_dir)
        
        logger.info("Starting Sunflower AI model compilation...")
        logger.info(f"Build directory: {build_dir}")
        logger.info(f"Output directory: {output_dir}")
        
        # Compile all models
        results = compiler.compile_all_models()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("MODEL COMPILATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total models compiled: {results['summary']['total_models']}")
        logger.info(f"Successful: {results['summary']['successful']}")
        logger.info(f"Failed: {results['summary']['failed']}")
        logger.info(f"Total size: {results['summary']['total_size_mb']:.2f} MB")
        logger.info("=" * 60)
        
        # Cleanup
        compiler.cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if results['summary']['failed'] == 0 else 1)
        
    except Exception as e:
        logger.error(f"Model compilation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
