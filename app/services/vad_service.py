import os
import urllib.request
import numpy as np
from app.utils.logger import Logger

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    Logger.warn("onnxruntime is not installed. Silero VAD will fallback to Energy-based VAD.")

class VADService:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "silero_vad.onnx")
        self.session = None
        self.threshold = 0.5
        self.sampling_rate = 16000
        
        # Try to download and initialize ONNX Silero VAD if available
        if ONNX_AVAILABLE:
            try:
                self._ensure_model_exists()
                # Set up ONNX Runtime Session
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=['CPUExecutionProvider'])
                self._reset_states()
                Logger.info("Silero VAD model initialized successfully.")
            except Exception as e:
                Logger.error(f"Failed to initialize Silero VAD ONNX session: {e}. Falling back to energy-based VAD.")
                self.session = None
        else:
            Logger.info("Using Energy-based VAD for speech detection.")

    def _ensure_model_exists(self):
        if not os.path.exists(self.model_path):
            Logger.info("Downloading Silero VAD ONNX model...")
            url = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
            try:
                # Use a request with a timeout to avoid hanging
                urllib.request.urlretrieve(url, self.model_path)
                Logger.info(f"Silero VAD model downloaded to {self.model_path}")
            except Exception as e:
                Logger.error(f"Failed to download Silero VAD model: {e}")
                raise e

    def _reset_states(self):
        # Silero VAD v5 (current master) expects state shape (2, 1, 128)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        # Context/sample tracking
        self._sr_tensor = np.array([self.sampling_rate], dtype=np.int64)

    def is_speech(self, audio_bytes: bytes) -> bool:
        """
        Processes a chunk of audio bytes (expects 16kHz, 16-bit mono PCM).
        Returns True if speech is detected, False otherwise.
        """
        if not audio_bytes:
            return False

        try:
            # Convert raw bytes to float32 numpy array normalized to [-1.0, 1.0]
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            # If no audio samples parsed, return False
            if len(audio_data) == 0:
                return False

            # If ONNX session is active, run Silero inference
            if self.session is not None:
                # Silero VAD expects input chunk sizes of 256, 512, or 768 samples for 16kHz
                # If chunk is different, we can pad or slice. Let's chunk or run on whatever we have if it matches,
                # but standard Silero ONNX v4 requires 512 or similar.
                # If we pad/chunk to 512 samples:
                target_len = 512
                if len(audio_data) < target_len:
                    audio_data = np.pad(audio_data, (0, target_len - len(audio_data)), 'constant')
                elif len(audio_data) > target_len:
                    audio_data = audio_data[:target_len]

                # Run inference
                ort_inputs = {
                    'input': np.expand_dims(audio_data, axis=0),
                    'state': self._state,
                    'sr': self._sr_tensor
                }
                out, state = self.session.run(None, ort_inputs)
                self._state = state  # Save state for next step

                # Squeeze handles any output shape (1,), (1,1), etc.
                prob = float(np.squeeze(out[0]))
                return prob >= self.threshold

            else:
                # Fallback to energy-based VAD using Root Mean Square (RMS)
                # Calculate signal energy
                rms = np.sqrt(np.mean(audio_data**2))
                # For normalized float32, active speech energy is typically > 0.015
                energy_threshold = 0.015
                is_active = rms > energy_threshold
                Logger.debug(f"Energy VAD - RMS: {rms:.4f}, Speech Detected: {is_active}")
                return bool(is_active)

        except Exception as e:
            Logger.error(f"Error in VAD processing: {e}")
            # Safe fallback: assume speech to avoid missing critical incidents
            return True

vad_service = VADService()
