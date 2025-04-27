from io import BytesIO
import math
from PIL import Image
from xml.etree.ElementTree import ElementTree, Element, SubElement
from Aslide.sdpc.sdpc_slide import SdpcSlide


class DeepZoomGenerator(object):
    """Generates Deep Zoom tiles and metadata for SDPC format slides."""

    def __init__(self, osr, tile_size=254, overlap=1, limit_bounds=False):
        """Create a DeepZoomGenerator wrapping an SDPC slide object.

        osr:          a slide object.
        tile_size:    the width and height of a single tile.  For best viewer
                      performance, tile_size + 2 * overlap should be a power
                      of two.
        overlap:      the number of extra pixels to add to each interior edge
                      of a tile.
        limit_bounds: True to render only the non-empty slide region."""

        self.slide = osr
        self._osr = osr

        # Store parameters
        self._z_t_downsample = tile_size
        self._z_overlap = overlap
        self._limit_bounds = limit_bounds

        # Get slide dimensions - SDPC stores dimensions in level_dimensions
        self._l0_dimensions = self._osr.level_dimensions[0]

        # Deep Zoom level dimensions and tiles
        z_dimensions = [self._l0_dimensions]
        z_size = tuple(self._l0_dimensions)

        # Build the Deep Zoom pyramid
        while z_size[0] > 1 or z_size[1] > 1:
            z_size = tuple(max(1, int(math.ceil(z / 2))) for z in z_size)
            z_dimensions.append(z_size)
        self._z_dimensions = tuple(reversed(z_dimensions))

        # Tile calculations
        tiles = lambda z_lim: int(math.ceil(z_lim / self._z_t_downsample))
        self._t_dimensions = tuple((tiles(z_w), tiles(z_h))
                    for z_w, z_h in self._z_dimensions)

        # Deep Zoom level count
        self._dz_levels = len(self._z_dimensions)

        # Total downsamples for each Deep Zoom level
        l0_z_downsamples = tuple(2 ** (self._dz_levels - dz_level - 1)
                    for dz_level in range(self._dz_levels))

        # Preferred slide levels for each Deep Zoom level
        # SDPC has its own get_best_level_for_downsample method
        self._slide_from_dz_level = tuple(
                    self._osr.get_best_level_for_downsample(d)
                    for d in l0_z_downsamples)

        # Piecewise downsamples
        self._l0_l_downsamples = self._osr.level_downsamples
        self._l_z_downsamples = tuple(
                    l0_z_downsamples[dz_level] /
                    self._l0_l_downsamples[self._slide_from_dz_level[dz_level]]
                    for dz_level in range(self._dz_levels))

        # Background color - use white as default
        self._bg_color = '#ffffff'

    def __repr__(self):
        return '%s(%r, tile_size=%r, overlap=%r, limit_bounds=%r)' % (
                self.__class__.__name__, self._osr, self._z_t_downsample,
                self._z_overlap, self._limit_bounds)

    @property
    def level_count(self):
        """The number of Deep Zoom levels in the image."""
        return self._dz_levels

    @property
    def level_tiles(self):
        """A list of (tiles_x, tiles_y) tuples for each Deep Zoom level."""
        return self._t_dimensions

    @property
    def level_dimensions(self):
        """A list of (pixels_x, pixels_y) tuples for each Deep Zoom level."""
        return self._z_dimensions

    @property
    def tile_count(self):
        """The total number of Deep Zoom tiles in the image."""
        return sum(t_cols * t_rows for t_cols, t_rows in self._t_dimensions)

    def _get_tile_info(self, level, address):
        """Calculate the appropriate tile information for a given level and address."""
        # Get preferred slide level
        slide_level = self._slide_from_dz_level[level]

        # Calculate tile position and size
        x, y = address
        tile_size = self._z_t_downsample

        # Calculate pixel offset for this tile
        z_overlap = self._z_overlap
        tile_x = (x * tile_size) - (x * z_overlap)
        tile_y = (y * tile_size) - (y * z_overlap)

        # Calculate pixel size for this tile
        z_size = self._z_dimensions[level]
        z_x = min(tile_size + (2 * z_overlap), z_size[0] - tile_x)
        z_y = min(tile_size + (2 * z_overlap), z_size[1] - tile_y)

        # Calculate downsampling factor
        l0_z_downsample = 2 ** (self._dz_levels - level - 1)

        # Calculate region in base level coordinates
        l0_x = int(tile_x * l0_z_downsample)
        l0_y = int(tile_y * l0_z_downsample)
        l0_z_x = int(z_x * l0_z_downsample)
        l0_z_y = int(z_y * l0_z_downsample)

        # Debug information
        if level < 13:
            print(f"_get_tile_info: level={level}, address={address}, slide_level={slide_level}")
            print(f"  tile_size={tile_size}, z_overlap={z_overlap}")
            print(f"  tile_x={tile_x}, tile_y={tile_y}")
            print(f"  z_size={z_size}, z_x={z_x}, z_y={z_y}")
            print(f"  l0_z_downsample={l0_z_downsample}")
            print(f"  l0_x={l0_x}, l0_y={l0_y}, l0_z_x={l0_z_x}, l0_z_y={l0_z_y}")

        # Return location, level, size
        return (l0_x, l0_y), slide_level, (l0_z_x, l0_z_y), (z_x, z_y)

    def _get_tile_from_level(self, level, address):
        """Get corresponding tile and not optimizing

        level:     the Deep Zoom level.
        address:   the address of the tile within the level as a (col, row) tuple.
        """
        # Read patch
        (l0_x, l0_y), slide_level, (l0_z_x, l0_z_y), (z_x, z_y) = self._get_tile_info(level, address)

        # Read region
        tile = self._osr.read_region((l0_x, l0_y), slide_level, (l0_z_x, l0_z_y))

        # Resize to correct region
        if tile.size != (z_x, z_y):
            tile = tile.resize((z_x, z_y), Image.LANCZOS)

        return tile

    def get_tile(self, level, address):
        """Return an RGB PIL.Image for a tile.

        level:     the Deep Zoom level.
        address:   the address of the tile within the level as a (col, row)
                   tuple."""

        # Get tile information
        (l0_x, l0_y), slide_level, (l0_z_x, l0_z_y), (z_x, z_y) = self._get_tile_info(level, address)

        # Performance Optimization: High resolution -> read_region get_thumbnail
        # Low resolution -> original deepzoom
        if level >= 13:
            print('Executing original deepzoom')
        elif 0 <= level < 13: # level 13 is an empirical parameter, it works fine on my server
            try:
                slide_level_count = len(self._osr.level_dimensions)

                # Get all slide level downsample factors
                slide_downsamples = self._osr.level_downsamples

                # Assign appropriate slide levels for different DeepZoom levels for progressive quality transition
                if level < 9:  # Very high resolution levels, use lowest resolution level
                    # Use the lowest resolution level (last level)
                    target_slide_level = slide_level_count - 1
                    print(f"  Very high resolution level {level} < 9, using lowest resolution slide level {target_slide_level}")
                elif level < 11:  # Higher resolution levels, use second-to-last level (if available)
                    target_slide_level = max(0, slide_level_count - 2)
                    print(f"  Higher resolution level {level} < 11, using slide level {target_slide_level}")
                elif level < 13:  # Medium resolution levels, use third-to-last level (if available)
                    target_slide_level = max(0, slide_level_count - 3)
                    # Ensure we don't use too high resolution levels (which may cause performance issues)
                    target_slide_level = min(target_slide_level, slide_level_count - 2)
                    print(f"  Medium resolution level {level} < 13, using slide level {target_slide_level}")
                else:  # Low resolution levels, can use more precise levels
                    # Calculate ideal downsample factor for current DeepZoom level
                    ideal_downsample = 2 ** level

                    # Find the closest slide level that is not smaller than half the ideal factor
                    target_slide_level = 0
                    min_diff = float('inf')

                    for i, downsample in enumerate(slide_downsamples):
                        # We want to find a downsample factor that is at least half the ideal factor
                        if downsample >= ideal_downsample / 2:
                            diff = abs(downsample - ideal_downsample)
                            if diff < min_diff:
                                min_diff = diff
                                target_slide_level = i

                # Calculate ideal downsample factor (if not already calculated)
                if 'ideal_downsample' not in locals():
                    ideal_downsample = 2 ** level

                print(f"  Selected slide level {target_slide_level}, downsample factor: {slide_downsamples[target_slide_level]}, ideal factor: {ideal_downsample}")

                # Calculate coordinates and dimensions in target slide level
                # First, calculate the global coordinates of the tile in current DeepZoom level
                x, y = address
                tile_size = self._z_t_downsample
                z_overlap = self._z_overlap

                # Calculate pixel coordinates of the tile in current level (top-left corner)
                tile_x = (x * tile_size) - (x * z_overlap)
                tile_y = (y * tile_size) - (y * z_overlap)

                # Calculate scale factor for current level (relative to DeepZoom level 0)
                # Higher DeepZoom levels have lower resolution, so scale factor is a power of 2
                dz_scale_factor = 2 ** level

                # For high resolution requests (level < 13), we use a simpler direct approach
                if level < 13:
                    # For high resolution levels, we use the thumbnail method
                    # Instead of calculating complex coordinate mappings, we get the entire image thumbnail

                    # Get target level dimensions
                    target_level_dims = self._osr.level_dimensions[target_slide_level]

                    # Use (0,0) coordinates to get the entire image
                    slide_x = 0
                    slide_y = 0

                    # Use smaller dimensions to avoid performance issues
                    # Different sizes for different levels
                    if level < 5:  # Very high resolution
                        max_dim = 64
                    elif level < 9:  # Medium-high resolution
                        max_dim = 128
                    else:  # Higher resolution
                        max_dim = 256

                    # Maintain aspect ratio
                    if target_level_dims[0] > target_level_dims[1]:
                        slide_width = min(max_dim, target_level_dims[0])
                        slide_height = int(target_level_dims[1] * (slide_width / target_level_dims[0]))
                    else:
                        slide_height = min(max_dim, target_level_dims[1])
                        slide_width = int(target_level_dims[0] * (slide_height / target_level_dims[1]))

                    # Ensure dimensions are not zero
                    slide_width = max(32, slide_width)
                    slide_height = max(32, slide_height)

                    # Calculate coordinates in level 0 (for read_region)
                    slide_scale = self._osr.level_downsamples[target_slide_level]
                    l0_tile_x = 0
                    l0_tile_y = 0

                    print(f"  Simplified method: Using whole image thumbnail, size: {slide_width}x{slide_height}")
                    print(f"  Target level dimensions: {target_level_dims}")
                else:
                    # For low resolution levels, use original coordinate mapping method
                    # Calculate coordinates in DeepZoom level 0 (highest resolution)
                    l0_tile_x = tile_x * dz_scale_factor
                    l0_tile_y = tile_y * dz_scale_factor

                    # Get scale factor for target slide level
                    slide_scale = self._osr.level_downsamples[target_slide_level]

                    # Calculate coordinates in target slide level
                    slide_x = int(l0_tile_x / slide_scale)
                    slide_y = int(l0_tile_y / slide_scale)

                    # Calculate dimensions in target slide level
                    slide_width = int(z_x * dz_scale_factor / slide_scale)
                    slide_height = int(z_y * dz_scale_factor / slide_scale)

                # Ensure dimensions are not zero
                slide_width = max(1, slide_width)
                slide_height = max(1, slide_height)

                print(f"  Using slide level: {target_slide_level}, coordinates: ({slide_x}, {slide_y}), size: {slide_width}x{slide_height}")
                print(f"  Original DeepZoom level: {level}, address: {address}, tile size: {z_x}x{z_y}")

                # Check if coordinates and dimensions are valid
                if slide_width <= 0 or slide_height <= 0:
                    print(f"  Warning: Invalid dimensions {slide_width}x{slide_height}, using default values")
                    slide_width = max(1, slide_width)
                    slide_height = max(1, slide_height)

                # Check if coordinates are within valid range
                if l0_tile_x < 0 or l0_tile_y < 0:
                    print(f"  Warning: Negative coordinates ({l0_tile_x}, {l0_tile_y}), adjusting to (0, 0)")
                    l0_tile_x = max(0, l0_tile_x)
                    l0_tile_y = max(0, l0_tile_y)

                # For levels below 13, we need to be especially careful to avoid service freezes
                if level < 13:
                    # For high resolution levels, we need to balance image quality and performance
                    # Use different maximum size limits for different levels
                    if level < 5:  # Very high resolution
                        max_size = 128  # Very strict limit
                    elif level < 9:  # Medium-high resolution
                        max_size = 256  # Stricter limit
                    else:  # Higher resolution
                        max_size = 384  # Moderate limit

                    original_width, original_height = slide_width, slide_height

                    if slide_width > max_size or slide_height > max_size:
                        print(f"  Warning: Size too large {slide_width}x{slide_height}, limiting to max {max_size}")
                        # Maintain aspect ratio
                        if slide_width > slide_height:
                            slide_height = max(1, int(slide_height * (max_size / slide_width)))
                            slide_width = max_size
                        else:
                            slide_width = max(1, int(slide_width * (max_size / slide_height)))
                            slide_height = max_size

                    # Ensure dimensions are not smaller than minimum value
                    min_size = 32  # Minimum size
                    slide_width = max(min_size, slide_width)
                    slide_height = max(min_size, slide_height)

                    print(f"  Size adjustment: Original {original_width}x{original_height} -> Final {slide_width}x{slide_height}")

                # For high resolution requests (level < 13), we use improved thumbnail method
                if level < 13:
                    try:
                        print(f"  Using improved thumbnail method")

                        # Get whole image thumbnail, adjust size and quality based on level
                        if level < 5:  # Very high resolution
                            thumb_size = 512
                        elif level < 9:  # Medium-high resolution
                            thumb_size = 768
                        elif level < 11:  # Higher resolution
                            thumb_size = 1024
                        else:  # Medium resolution
                            thumb_size = 1536  # Higher quality thumbnail

                        # Get original slide dimensions
                        original_width, original_height = self._l0_dimensions

                        # Calculate appropriate thumbnail dimensions, maintaining aspect ratio
                        if original_width > original_height:
                            thumb_width = thumb_size
                            thumb_height = int(original_height * (thumb_size / original_width))
                        else:
                            thumb_height = thumb_size
                            thumb_width = int(original_width * (thumb_size / original_height))

                        print(f"  Getting thumbnail, target size: {thumb_width}x{thumb_height}, level: {level}")
                        full_thumbnail = self._osr.get_thumbnail((thumb_width, thumb_height))

                        if full_thumbnail:
                            print(f"  Got complete thumbnail, size: {full_thumbnail.size}")

                            # Calculate current tile position in the complete thumbnail

                            # Calculate relative position of current tile in current level (0.0-1.0)
                            # Use tile address to calculate relative position
                            x, y = address

                            # Get total dimensions of current level
                            level_width, level_height = self._z_dimensions[level]

                            # Calculate pixel coordinates of current tile in current level
                            tile_size = self._z_t_downsample
                            z_overlap = self._z_overlap

                            # Calculate top-left pixel coordinates of tile (considering overlap)
                            pixel_x = (x * tile_size) - (x * z_overlap)
                            pixel_y = (y * tile_size) - (y * z_overlap)

                            # Calculate relative position (0.0-1.0)
                            rel_x = pixel_x / level_width
                            rel_y = pixel_y / level_height

                            # Calculate position of current tile in complete thumbnail
                            thumb_x = int(rel_x * full_thumbnail.size[0])
                            thumb_y = int(rel_y * full_thumbnail.size[1])

                            # Calculate size of area to crop
                            # Use same relative size as current tile
                            rel_width = z_x / level_width
                            rel_height = z_y / level_height

                            thumb_width = max(1, int(rel_width * full_thumbnail.size[0]))
                            thumb_height = max(1, int(rel_height * full_thumbnail.size[1]))

                            # Ensure we don't exceed thumbnail boundaries
                            thumb_x = min(thumb_x, full_thumbnail.size[0] - thumb_width)
                            thumb_y = min(thumb_y, full_thumbnail.size[1] - thumb_height)

                            # Crop the area corresponding to current tile
                            crop_box = (thumb_x, thumb_y, thumb_x + thumb_width, thumb_y + thumb_height)
                            print(f"  Crop area: {crop_box}")

                            try:
                                thumbnail = full_thumbnail.crop(crop_box)

                                # Resize to requested dimensions
                                if thumbnail.size != (z_x, z_y):
                                    thumbnail = thumbnail.resize((z_x, z_y), Image.LANCZOS)

                                print(f"  Cropped and resized thumbnail size: {thumbnail.size}")
                                return thumbnail
                            except Exception as e:
                                print(f"  Failed to crop thumbnail: {e}")
                                # If cropping fails, try returning resized complete thumbnail
                                thumbnail = full_thumbnail.resize((z_x, z_y), Image.LANCZOS)
                                return thumbnail
                    except Exception as e:
                        print(f"  Improved thumbnail method failed: {e}")
                        # If improved thumbnail method fails, continue with other methods

                # Directly use read_region to get image
                try:
                    # Set timeout (seconds)
                    import signal

                    def timeout_handler(signum, frame):
                        # Parameters are required but not used in function body
                        # Use # noqa comment to suppress unused variable warnings
                        raise TimeoutError("Image reading timeout")

                    # Set different timeout times based on level
                    if level < 5:  # Very high resolution
                        timeout = 2  # Very short timeout
                    elif level < 9:  # Medium-high resolution
                        timeout = 3  # Shorter timeout
                    elif level < 13:  # Higher resolution
                        timeout = 5  # Short timeout
                    else:
                        timeout = 30  # Normal timeout

                    print(f"  Setting timeout: {timeout} seconds")

                    # Set timeout handler
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout)

                    try:
                        # For high resolution requests (level < 13), we use safer parameters
                        if level < 13:
                            # Use center area of lowest resolution level
                            # This avoids requesting edge areas of the image, which may cause read failures
                            target_level_dims = self._osr.level_dimensions[target_slide_level]

                            # Calculate center area
                            center_x = target_level_dims[0] // 2
                            center_y = target_level_dims[1] // 2

                            # Use smaller dimensions
                            safe_width = min(128, target_level_dims[0])
                            safe_height = min(128, target_level_dims[1])

                            # Calculate top-left coordinates
                            safe_x = max(0, center_x - (safe_width // 2))
                            safe_y = max(0, center_y - (safe_height // 2))

                            # Calculate coordinates in level 0
                            slide_scale = self._osr.level_downsamples[target_slide_level]
                            safe_l0_x = int(safe_x * slide_scale)
                            safe_l0_y = int(safe_y * slide_scale)

                            print(f"  Using safe parameters: coordinates ({safe_l0_x}, {safe_l0_y}), size {safe_width}x{safe_height}")
                            tile = self._osr.read_region((safe_l0_x, safe_l0_y), target_slide_level, (safe_width, safe_height))
                        else:
                            # For low resolution levels, use original parameters
                            tile = self._osr.read_region((l0_tile_x, l0_tile_y), target_slide_level, (slide_width, slide_height))

                        # Cancel timeout
                        signal.alarm(0)

                        # Resize to requested dimensions
                        if tile.size != (z_x, z_y):
                            tile = tile.resize((z_x, z_y), Image.LANCZOS)

                        return tile
                    except TimeoutError as te:
                        print(f"  Image reading timeout: {te}")
                        # If timeout, return blank image
                        return Image.new('RGB', (z_x, z_y), self._bg_color)
                    finally:
                        # Restore original signal handler
                        signal.signal(signal.SIGALRM, old_handler)
                        signal.alarm(0)

                except Exception as e:
                    print(f"  read_region failed: {e}")
                    # If all methods fail, return blank image
                    return Image.new('RGB', (z_x, z_y), self._bg_color)
            except Exception as e:
                print(f"Direct read_region processing for level {level} failed: {e}")
                # If failed, try using original method
                pass

        # Use original DeepZoom processing method (for level >= 13 or when direct read_region fails)
        try:
            # Read region
            print(f"Using original DeepZoom method for level {level}, slide level {slide_level}")

            # Set timeout (seconds)
            import signal

            def timeout_handler(signum, frame):
                # Parameters are required but not used in function body
                # Use # noqa comment to suppress unused variable warnings
                raise TimeoutError("Original method image reading timeout")

            # Set timeout handler
            timeout = 30  # Normal timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

            try:
                tile = self._osr.read_region((l0_x, l0_y), slide_level, (l0_z_x, l0_z_y))

                # Cancel timeout
                signal.alarm(0)

                # Resize to correct dimensions
                if tile.size != (z_x, z_y):
                    tile = tile.resize((z_x, z_y), Image.LANCZOS)

                return tile
            except TimeoutError as te:
                print(f"  Original method image reading timeout: {te}")
                # If timeout, return blank image
                return Image.new('RGB', (z_x, z_y), self._bg_color)
            finally:
                # Restore original signal handler
                signal.signal(signal.SIGALRM, old_handler)
                signal.alarm(0)

        except Exception as e:
            # If reading fails, return blank tile
            print(f"Error reading tile at level {level}, address {address}: {e}")
            return Image.new('RGB', (z_x, z_y), self._bg_color)

    def get_dzi(self, format):
        """Return a string containing the XML metadata for the .dzi file.

        format:    the format of the individual tiles ('png' or 'jpeg')"""
        image = Element('Image', TileSize=str(self._z_t_downsample),
                        Overlap=str(self._z_overlap), Format=format,
                        xmlns='http://schemas.microsoft.com/deepzoom/2008')
        w, h = self._l0_dimensions
        SubElement(image, 'Size', Width=str(w), Height=str(h))
        tree = ElementTree(element=image)
        buf = BytesIO()
        tree.write(buf, encoding='UTF-8')
        return buf.getvalue().decode('UTF-8')


def main():
    """Test function for the SDPC DeepZoomGenerator."""
    import sys
    if len(sys.argv) != 2:
        print('Usage: %s <sdpc-file>' % sys.argv[0])
        sys.exit(1)

    sdpc_path = sys.argv[1]
    try:
        slide = SdpcSlide(sdpc_path)

        print("SDPC Slide Information:")
        print("Level count:", slide.level_count)
        print("Level dimensions:", slide.level_dimensions)
        print("Level downsamples:", slide.level_downsamples)

        dzg = DeepZoomGenerator(slide)
        print("\nDeepZoom Generator Information:")
        print("DeepZoom level count:", dzg.level_count)
        print("DeepZoom level tiles:", dzg.level_tiles)
        print("DeepZoom level dimensions:", dzg.level_dimensions)
        print("DeepZoom tile count:", dzg.tile_count)
        print("\nDZI XML:")
        print(dzg.get_dzi('jpeg'))

        # Get sample tiles from different levels
        if dzg.level_count > 0:
            # Get the lowest resolution tile (highest level)
            highest_level = dzg.level_count - 1
            tile_highest = dzg.get_tile(highest_level, (0, 0))
            tile_highest.save('sdpc_tile_highest.jpg')
            print(f"Sample tile from highest level ({highest_level}) saved as 'sdpc_tile_highest.jpg'")

            # Get a mid-resolution tile if available
            if dzg.level_count > 2:
                mid_level = dzg.level_count // 2
                tile_mid = dzg.get_tile(mid_level, (0, 0))
                tile_mid.save('sdpc_tile_mid.jpg')
                print(f"Sample tile from mid level ({mid_level}) saved as 'sdpc_tile_mid.jpg'")

            # Get the highest resolution tile (lowest level) if not too large
            if dzg.level_count > 1:
                tile_lowest = dzg.get_tile(0, (0, 0))
                tile_lowest.save('sdpc_tile_lowest.jpg')
                print(f"Sample tile from lowest level (0) saved as 'sdpc_tile_lowest.jpg'")
    except Exception as e:
        print(f"Error testing SDPC DeepZoom: {e}")
    finally:
        if 'slide' in locals():
            slide.close()
            print("SDPC slide closed")


if __name__ == '__main__':
    main()