"""
VSI format data structures.
Based on Bio-Formats CellSensReader implementation.
Licensed under GPL v2+ (compatible with Bio-Formats license)
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class TileCoordinate:
    """Represents a tile coordinate in multi-dimensional space."""
    coordinate: List[int]
    
    def __init__(self, n_dimensions: int):
        self.coordinate = [0] * n_dimensions
    
    def __eq__(self, other):
        if not isinstance(other, TileCoordinate):
            return False
        return self.coordinate == other.coordinate
    
    def __str__(self):
        return "{" + ", ".join(map(str, self.coordinate)) + "}"


@dataclass
class Pyramid:
    """Represents a pyramid/series in the VSI file."""
    name: Optional[str] = None
    
    # Objective properties
    magnification: Optional[float] = None
    numerical_aperture: Optional[float] = None
    objective_name: Optional[str] = None
    refractive_index: Optional[float] = None
    working_distance: Optional[float] = None
    
    # Image dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    tile_origin_x: Optional[int] = None
    tile_origin_y: Optional[int] = None
    origin_x: Optional[float] = None
    origin_y: Optional[float] = None
    physical_size_x: Optional[float] = None
    physical_size_y: Optional[float] = None
    acquisition_time: Optional[int] = None
    bit_depth: Optional[int] = None
    
    # Camera settings
    binning_x: Optional[int] = None
    binning_y: Optional[int] = None
    gain: Optional[float] = None
    offset: Optional[float] = None
    
    # Color channel gains and offsets
    red_gain: Optional[float] = None
    green_gain: Optional[float] = None
    blue_gain: Optional[float] = None
    red_offset: Optional[float] = None
    green_offset: Optional[float] = None
    blue_offset: Optional[float] = None
    
    # Channel information
    channel_names: List[str] = field(default_factory=list)
    channel_wavelengths: List[float] = field(default_factory=list)
    exposure_times: List[int] = field(default_factory=list)
    other_exposure_times: List[int] = field(default_factory=list)
    default_exposure_time: Optional[int] = None
    
    # Objective information
    objective_names: List[str] = field(default_factory=list)
    objective_types: List[int] = field(default_factory=list)
    
    # Device information
    device_names: List[str] = field(default_factory=list)
    device_types: List[str] = field(default_factory=list)
    device_ids: List[str] = field(default_factory=list)
    device_manufacturers: List[str] = field(default_factory=list)
    
    # Metadata
    original_metadata: Dict[str, Any] = field(default_factory=dict)
    dimension_ordering: Dict[str, int] = field(default_factory=dict)
    
    # Z-stack information
    z_start: Optional[float] = None
    z_increment: Optional[float] = None
    z_values: List[float] = field(default_factory=list)
    
    # External file flag
    has_associated_ets_file: bool = False


@dataclass
class VsiMetadata:
    """Container for VSI file metadata."""
    pyramids: List[Pyramid] = field(default_factory=list)
    used_files: List[str] = field(default_factory=list)
    extra_files: List[str] = field(default_factory=list)
    file_map: Dict[int, str] = field(default_factory=dict)
    
    # Tile information
    tile_offsets: List[List[int]] = field(default_factory=list)
    rows: List[int] = field(default_factory=list)
    cols: List[int] = field(default_factory=list)
    compression_type: List[int] = field(default_factory=list)
    tile_x: List[int] = field(default_factory=list)
    tile_y: List[int] = field(default_factory=list)
    
    # Tile mapping
    tile_map: List[List[TileCoordinate]] = field(default_factory=list)
    n_dimensions: List[int] = field(default_factory=list)
    
    # Background colors
    background_color: Dict[int, bytes] = field(default_factory=dict)
    
    # Flags
    expect_ets: bool = False
    jpeg: bool = False
    bgr: List[bool] = field(default_factory=list)
    
    # Dimension tracking
    in_dimension_properties: bool = False
    found_channel_tag: bool = False
    dimension_tag: int = 0
    metadata_index: int = -1
    previous_tag: int = 0
    channel_count: int = 0
    z_count: int = 0


@dataclass
class VsiTileInfo:
    """Information about a tile in the VSI file."""
    offset: int
    size: int
    compression: int
    coordinate: TileCoordinate
    
    
@dataclass
class VsiSeriesInfo:
    """Information about a series/pyramid in the VSI file."""
    pyramid: Pyramid
    level_count: int
    level_dimensions: List[Tuple[int, int]]
    level_downsamples: List[float]
    tile_info: List[List[VsiTileInfo]]  # [level][tile_index]
    properties: Dict[str, str]
    associated_images: Dict[str, Any]
