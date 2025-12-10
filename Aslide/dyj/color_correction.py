"""
Color Correction module for DYJ format.

Implements color correction based on LUT (Look-Up Table) files from d-Viewer.
The LUT file contains:
- gamma: Gamma correction value
- ccm: 3x3 Color Correction Matrix (row-major order)
- rgbRate: RGB channel gains
- hsvRate: HSV adjustment factors

Color correction pipeline:
1. Apply gamma correction
2. Apply CCM (Color Correction Matrix)
3. Apply RGB channel gains
4. Apply HSV adjustments (if enabled)
"""

import os
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Tuple
import numpy as np
from PIL import Image


class ColorCorrection:
    """Color correction processor for DYJ images."""

    # Default LUT directory (relative to this file)
    LUT_DIR = os.path.join(os.path.dirname(__file__), 'lut')

    # Predefined LUT styles (aligned with SDPC naming)
    STYLES = {
        'Real': 'real.lut',
        'Gorgeous': 'real2.lut',
    }

    def __init__(self, style: str = 'Real', lut_path: Optional[str] = None):
        """Initialize color correction with a LUT file.

        Args:
            style: Predefined style name ('Real' or 'Real2')
            lut_path: Custom LUT file path (overrides style if provided)
        """
        self._enabled = False
        self._gamma = 1.0
        self._ccm = np.eye(3, dtype=np.float32)  # Identity matrix
        self._rgb_rate = np.ones(3, dtype=np.float32)
        self._hsv_rate = np.ones(3, dtype=np.float32)
        self._style = style

        # Load LUT file
        if lut_path:
            self._load_lut(lut_path)
        elif style in self.STYLES:
            lut_file = os.path.join(self.LUT_DIR, self.STYLES[style])
            if os.path.exists(lut_file):
                self._load_lut(lut_file)

    def _load_lut(self, lut_path: str):
        """Load LUT configuration from XML file.

        Args:
            lut_path: Path to the LUT file
        """
        try:
            tree = ET.parse(lut_path)
            root = tree.getroot()

            # Parse gamma
            gamma_elem = root.find('gamma')
            if gamma_elem is not None and gamma_elem.text:
                self._gamma = float(gamma_elem.text)

            # Parse CCM (3x3 matrix, row-major)
            ccm_elem = root.find('ccm')
            if ccm_elem is not None:
                floats = [float(f.text) for f in ccm_elem.findall('float')]
                if len(floats) == 9:
                    self._ccm = np.array(floats, dtype=np.float32).reshape(3, 3)

            # Parse RGB rate
            rgb_elem = root.find('rgbRate')
            if rgb_elem is not None:
                floats = [float(f.text) for f in rgb_elem.findall('float')]
                if len(floats) == 3:
                    self._rgb_rate = np.array(floats, dtype=np.float32)

            # Parse HSV rate
            hsv_elem = root.find('hsvRate')
            if hsv_elem is not None:
                floats = [float(f.text) for f in hsv_elem.findall('float')]
                if len(floats) == 3:
                    self._hsv_rate = np.array(floats, dtype=np.float32)

        except Exception as e:
            print(f"Warning: Failed to load LUT file {lut_path}: {e}")

    @property
    def enabled(self) -> bool:
        """Check if color correction is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable color correction."""
        self._enabled = value

    @property
    def style(self) -> str:
        """Get current style name."""
        return self._style

    def set_style(self, style: str):
        """Change color correction style.

        Args:
            style: Style name ('Real' or 'Real2')
        """
        if style in self.STYLES:
            lut_file = os.path.join(self.LUT_DIR, self.STYLES[style])
            if os.path.exists(lut_file):
                self._load_lut(lut_file)
                self._style = style

    def apply(self, image: Image.Image) -> Image.Image:
        """Apply color correction to an image.

        Args:
            image: Input PIL Image (RGB or RGBA)

        Returns:
            Color-corrected PIL Image
        """
        if not self._enabled:
            return image

        # Convert to numpy array
        has_alpha = image.mode == 'RGBA'
        if has_alpha:
            img_array = np.array(image, dtype=np.float32)
            rgb = img_array[:, :, :3]
            alpha = img_array[:, :, 3:4]
        else:
            rgb = np.array(image.convert('RGB'), dtype=np.float32)
            alpha = None

        # Normalize to [0, 1]
        rgb = rgb / 255.0

        # 1. Apply gamma correction
        if self._gamma != 1.0:
            rgb = np.power(np.clip(rgb, 0, 1), self._gamma)

        # 2. Apply CCM (Color Correction Matrix)
        # Reshape for matrix multiplication: (H, W, 3) -> (H*W, 3)
        h, w = rgb.shape[:2]
        rgb_flat = rgb.reshape(-1, 3)
        # CCM is applied as: output = input @ CCM.T
        rgb_flat = rgb_flat @ self._ccm.T
        rgb = rgb_flat.reshape(h, w, 3)

        # 3. Apply RGB channel gains
        rgb = rgb * self._rgb_rate

        # Clip to valid range and convert back to uint8
        rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)

        # Reconstruct image
        if has_alpha:
            result = np.concatenate([rgb, alpha.astype(np.uint8)], axis=2)
            return Image.fromarray(result, mode='RGBA')
        else:
            return Image.fromarray(rgb, mode='RGB')

    def get_info(self) -> Dict:
        """Get color correction parameters info."""
        return {
            'enabled': self._enabled,
            'style': self._style,
            'gamma': self._gamma,
            'ccm': self._ccm.tolist(),
            'rgb_rate': self._rgb_rate.tolist(),
            'hsv_rate': self._hsv_rate.tolist(),
        }

