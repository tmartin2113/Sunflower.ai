import logging
from src.platform.hardware_detector import get_total_vram_gb
from src.config import get_model_registry

logger = logging.getLogger(__name__)

class ModelSelector:
    """
    Selects the optimal AI model based on available hardware resources.

    This class evaluates the system's VRAM and compares it against the
    requirements of available models listed in the model registry. It
    chooses the most capable model that the hardware can support.
    """

    def __init__(self):
        """Initializes the ModelSelector."""
        self.model_registry = get_model_registry()
        self.system_vram_gb = get_total_vram_gb()
        logger.info(f"Initialized ModelSelector with {self.system_vram_gb:.2f} GB of VRAM.")

    def select_optimal_model(self):
        """
        Selects the best model based on available VRAM.

        The selection logic iterates through the models in the registry,
        which are assumed to be ordered from most to least capable.
        It returns the first model for which the system's VRAM meets
        the minimum requirement.

        Returns:
            dict: The registry entry for the selected model, or None if
                  no suitable model is found.
        """
        logger.info("Selecting optimal model for the current hardware...")
        
        # Sort models by required VRAM in descending order to find the best fit first
        sorted_models = sorted(
            self.model_registry.values(),
            key=lambda x: x.get('min_vram_gb', 0),
            reverse=True
        )

        for model_info in sorted_models:
            model_name = model_info.get('name')
            required_vram = model_info.get('min_vram_gb')

            if not model_name or required_vram is None:
                logger.warning(f"Skipping invalid model entry: {model_info}")
                continue

            logger.debug(f"Evaluating model '{model_name}': Requires {required_vram} GB VRAM, System has {self.system_vram_gb:.2f} GB.")
            if self.system_vram_gb >= required_vram:
                logger.info(f"Optimal model selected: '{model_name}'")
                return model_info

        logger.error("No suitable model found for the available hardware resources.")
        return None

    def get_fallback_model(self):
        """
        Returns the model with the lowest VRAM requirement as a fallback.
        
        Returns:
            dict: The registry entry for the least demanding model.
        """
        logger.warning("Falling back to the least demanding model.")
        sorted_models = sorted(
            self.model_registry.values(),
            key=lambda x: x.get('min_vram_gb', 999)
        )
        return sorted_models[0] if sorted_models else None
