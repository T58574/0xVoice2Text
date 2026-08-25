from abc import ABC, abstractmethod
from typing import Callable, Optional
import numpy as np

class BaseTTSAdapter(ABC):
    """
    Abstract base class for all TTS (Text-to-Speech) engine adapters.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns human-readable name of the TTS adapter."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Returns current status text."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the engine is ready for speech synthesis."""
        pass

    @abstractmethod
    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        """Asynchronously initializes model weights / clients."""
        pass

    @abstractmethod
    def synthesize_to_file(self, text: str, output_path: str, voice_params: Optional[dict] = None) -> bool:
        """
        Synthesizes speech for the given text and saves audio to output_path (.wav/.mp3).
        Returns True on success, False otherwise.
        """
        pass

    def synthesize_audio(self, text: str, voice_params: Optional[dict] = None) -> Optional[np.ndarray]:
        """Optional direct numpy audio buffer synthesis."""
        return None

    def unload(self) -> None:
        """Optional resource cleanup."""
        pass
