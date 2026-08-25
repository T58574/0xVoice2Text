from abc import ABC, abstractmethod
from typing import Callable, Optional
import numpy as np

class BaseSTTAdapter(ABC):
    """
    Abstract base class for all STT (Speech-to-Text) engine adapters.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns human-readable name of the STT adapter."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Returns current operational status text (e.g. 'READY', 'LOADING', 'ERROR')."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the engine is ready for transcription."""
        pass

    @abstractmethod
    def load_model(self, on_complete: Optional[Callable[[bool], None]] = None) -> None:
        """
        Asynchronously loads weights, initializes clients or preallocates compute resources.
        Calls on_complete(success: bool) when finished.
        """
        pass

    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "ru") -> str:
        """
        Transcribes 1D float32 numpy audio array (normalized [-1.0, 1.0]) into text.
        """
        pass

    def unload(self) -> None:
        """Optional resource cleanup hook."""
        pass
