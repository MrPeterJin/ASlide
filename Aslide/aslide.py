import os

from PIL import Image
from openslide import OpenSlide
from Aslide.kfb.kfb_slide import KfbSlide
from Aslide.tmap.tmap_slide import TmapSlide
from Aslide.sdpc.sdpc_slide import SdpcSlide
from Aslide.vsi.vsi_slide import VsiSlide
from Aslide.tron.slide import TronSlide
from Aslide.mds.mds_slide import MdsSlide
from Aslide.qptiff.qptiff_slide import QptiffSlide
from Aslide.isyntax.isyntax_slide import IsyntaxSlide
from Aslide.dyj.dyj_slide import DyjSlide
from Aslide.ibl.ibl_slide import IblSlide
from Aslide.zyp.zyp_slide import ZypSlide
from Aslide.bif.bif_slide import BifSlide


class Slide(object):
	def __init__(self, filepath):
		self.filepath = filepath
		self.format = os.path.splitext(os.path.basename(filepath))[-1]

		# try reader one by one
		# Try specific format readers first, then fall back to OpenSlide

		read_success = False

		# 1. qptiff (try first to avoid OpenSlide reading it as generic TIFF)
		if not read_success and self.format in ['.qptiff', '.QPTIFF'] and QptiffSlide:
			try:
				self._osr = QptiffSlide(filepath)
				read_success = True
			except:
				pass

		# 2. kfb
		if not read_success and self.format in ['.kfb', '.KFB']:
			try:
				self._osr = KfbSlide(filepath)
				read_success = True
			except:
				pass

		# 3. tmap
		if not read_success and self.format in ['.tmap', '.TMAP']:
			try:
				self._osr = TmapSlide(filepath)
				if self._osr:
					read_success = True
			except:
				pass

		# 4. sdpc / dyqx (both use sqrayslide SDK)
		if not read_success and self.format in ['.sdpc', '.SDPC', '.dyqx', '.DYQX']:
			try:
				self._osr = SdpcSlide(filepath)
				if self._osr:
					read_success = True
			except:
				pass

		# 5. vsi
		if not read_success and self.format in ['.vsi', '.VSI']:
			try:
				self._osr = VsiSlide(filepath)
				read_success = True
			except:
				pass

		# 6. mds/mdsx
		if not read_success and self.format in ['.mds', '.MDS', '.mdsx', '.MDSX'] and MdsSlide:
			try:
				self._osr = MdsSlide(filepath)
				read_success = True
			except:
				pass

		# 7. tron
		if not read_success and self.format in ['.tron', '.TRON']:
			try:
				self._osr = TronSlide(filepath)
				read_success = True
			except:
				pass

		# 8. isyntax
		if not read_success and self.format in ['.isyntax', '.ISYNTAX'] and IsyntaxSlide:
			try:
				self._osr = IsyntaxSlide(filepath)
				read_success = True
			except:
				pass

		# 9. dyj
		if not read_success and self.format in ['.dyj', '.DYJ']:
			try:
				self._osr = DyjSlide(filepath)
				read_success = True
			except:
				pass

		# 10. ibl
		if not read_success and self.format in ['.ibl', '.IBL']:
			try:
				self._osr = IblSlide(filepath)
				read_success = True
			except:
				pass

		# 11. zyp
		if not read_success and self.format in ['.zyp', '.ZYP']:
			try:
				self._osr = ZypSlide(filepath)
				read_success = True
			except:
				pass

		# 12. bif
		if not read_success and self.format in ['.bif', '.BIF']:
			try:
				self._osr = BifSlide(filepath)
				read_success = True
			except:
				pass

		# 13. openslide (fallback for generic formats)
		if not read_success:
			try:
				self._osr = OpenSlide(filepath)
				read_success = True
			except:
				pass

		if not read_success:
			raise Exception("UnsupportedFormat or ReadingFailed => %s" % filepath)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, exc_tb):
		self._osr.close()
		if exc_tb:
			return False

		return True

	@property
	def mpp(self):
		# First try the slide's own mpp property if it exists
		if hasattr(self._osr, 'mpp') and self._osr.mpp is not None:
			return self._osr.mpp

		# Fallback to properties
		if hasattr(self._osr, 'properties'):
			if 'openslide.mpp-x' in self._osr.properties and 'openslide.mpp-y' in self._osr.properties:
				mpp_x = float(self._osr.properties['openslide.mpp-x'])
				mpp_y = float(self._osr.properties['openslide.mpp-y'])
				return (mpp_x + mpp_y) / 2
			elif 'openslide.mpp-x' in self._osr.properties:
				return float(self._osr.properties['openslide.mpp-x'])

		# Fallback to calculating from scan_scale/magnification if possible
		if hasattr(self._osr, 'get_scan_scale'):
			scale = self._osr.get_scan_scale() if callable(self._osr.get_scan_scale) else self._osr.get_scan_scale
			if scale and scale > 0:
				return 10.0 / scale

		raise Exception("%s Has no attribute %s" % (self._osr.__class__.__name__, "mpp"))

	@property
	def magnification(self):
		"""
		Get the magnification of the slide.
		Calculates from mpp if not directly available.
		:return: float
		"""
		# 1. Try if the underlying slide has a magnification property
		if hasattr(self._osr, 'magnification') and self._osr.magnification is not None:
			return self._osr.magnification

		# 2. Try get_scan_scale (common in TMAP)
		if hasattr(self._osr, 'get_scan_scale'):
			scale = self._osr.get_scan_scale() if callable(self._osr.get_scan_scale) else self._osr.get_scan_scale
			if scale:
				return float(scale)

		# 3. Try to get objective power from properties
		if hasattr(self._osr, 'properties'):
			# Check common keys across different formats
			for key in ['openslide.objective-power', 'sdpc.magnification', 'ventana.Magnification']:
				if key in self._osr.properties:
					try:
						return float(self._osr.properties[key])
					except (ValueError, TypeError):
						pass

		# 4. Fallback to calculating from MPP if possible
		try:
			mpp = self.mpp # Using the property above which handles various sources
			if mpp and mpp > 0:
				return 10.0 / mpp
		except:
			pass

		return None

	@property
	def level_count(self):
		return self._osr.level_count

	@property
	def dimensions(self):
		return self._osr.dimensions

	@property
	def level_dimensions(self):
		return self._osr.level_dimensions

	@property
	def level_downsamples(self):
		return self._osr.level_downsamples

	@property
	def properties(self):
		return self._osr.properties

	@property
	def associated_images(self):
		"""Get associated images"""
		# Check if we have cached associated images
		if hasattr(self, '_cached_associated_images'):
			return self._cached_associated_images

		result = {}

		if hasattr(self._osr, 'associated_images'):
			assoc = self._osr.associated_images

			# Handle different interface types
			if callable(assoc):
				# TMAP-style method interface - convert to dict
				for tag in ['thumbnail', 'label', 'macro']:
					try:
						img = assoc(tag)
						if img is not None:
							result[tag] = img
					except:
						pass
			else:
				# Standard dict interface (KFB, SDPC)
				# For KFB, preload all images to avoid "closed slide" errors
				if hasattr(assoc, '_keys') and hasattr(assoc, '__getitem__'):
					# This is likely a KFB _AssociatedImageMap - preload all images
					try:
						keys = assoc._keys()
						for key in keys:
							try:
								result[key] = assoc[key]
							except:
								pass
					except:
						# If preloading fails, try to copy what we can
						pass
				elif isinstance(assoc, dict):
					# Standard dict (SDPC, MDS, etc.) - copy it
					result = dict(assoc)
				else:
					# Other dict-like objects
					try:
						result = dict(assoc)
					except:
						pass

		# Auto-generate thumbnail if not present
		if 'thumbnail' not in result:
			try:
				# Generate thumbnail from lowest resolution level
				# Use a reasonable default size
				thumbnail = self._generate_thumbnail_from_slide((512, 512))
				if thumbnail is not None:
					result['thumbnail'] = thumbnail
			except:
				pass

		# Cache the result
		self._cached_associated_images = result
		return result

	def _generate_thumbnail_from_slide(self, size):
		"""Generate thumbnail from the lowest resolution level of the slide.

		Args:
			size: (width, height) tuple for thumbnail size

		Returns:
			PIL Image or None if generation fails
		"""
		try:
			# Read from the highest level (lowest resolution)
			highest_level = self.level_count - 1
			level_dims = self.level_dimensions[highest_level]

			# Read the entire highest level or a reasonable portion
			read_width = min(level_dims[0], 2048)
			read_height = min(level_dims[1], 2048)

			thumbnail = self._osr.read_region((0, 0), highest_level, (read_width, read_height))

			# Convert to RGB if necessary (some formats return RGBA)
			if thumbnail.mode == 'RGBA':
				# Create white background and paste
				background = Image.new('RGB', thumbnail.size, (255, 255, 255))
				background.paste(thumbnail, mask=thumbnail.split()[3])
				thumbnail = background
			elif thumbnail.mode != 'RGB':
				thumbnail = thumbnail.convert('RGB')

			# Resize to target size while maintaining aspect ratio
			thumbnail.thumbnail(size, Image.LANCZOS)
			return thumbnail
		except Exception:
			return None

	def label_image(self, save_path):
		if self.format in ['.tmap', '.TMAP']:
			return self._osr.associated_images('label')
		elif self.format in ['.sdpc', '.SDPC', '.dyqx', '.DYQX']:
			return self._osr.saveLabelImg(save_path)
		else:
			return self._osr.associated_images.get('label', None)

	def get_best_level_for_downsample(self, downsample):
		return self._osr.get_best_level_for_downsample(downsample)

	def get_thumbnail(self, size):
		"""
		get thumbnail
		:param size:  (tuple) – (width, height) tuple giving the size of the thumbnail
		:return:
		"""
		return self._osr.get_thumbnail(size)

	def read_region(self, location, level, size):
		"""
		return region image
		:param location:  (tuple) – (x, y) tuple giving the top left pixel in the level 0 reference frame
		:param level:  (int) – the level number
		:param size:  (tuple) – (width, height) tuple giving the region size
		:return: PIL.Image object in RGBA mode
		"""
		img = self._osr.read_region(location, level, size)
		# Ensure consistent RGBA mode across all formats
		if img.mode != 'RGBA':
			img = img.convert('RGBA')
		return img

	def read_fixed_region(self, location, level, size):
		"""
		return region image
		:param location:  (tuple) – (x, y) tuple giving the top left pixel in the level 0 reference frame
		:param level:  (int) – the level number
		:param size:  (tuple) – (width, height) tuple giving the region size
		:return: PIL.Image object in RGBA mode
		"""
		img = self._osr.read_fixed_region(location, level, size)
		# Ensure consistent RGBA mode across all formats
		if img.mode != 'RGBA':
			img = img.convert('RGBA')
		return img

	def close(self):
		self._osr.close()

	def apply_color_correction(self, apply=True, style="Real"):
		"""
		Apply or disable color correction (SDPC, DYQX, DYJ, KFB, MDS, MDSX and TMAP formats)

		Args:
			apply: Whether to apply color correction
			style: Color correction style
			       - SDPC/DYQX: "Real" or "Gorgeous"
			       - DYJ: "Real" or "Gorgeous"
			       - KFB: "Real"
			       - MDS/MDSX: "Real"
			       - TMAP: "Real"
		"""
		if self.format in ['.sdpc', '.SDPC', '.dyqx', '.DYQX']:
			self._osr.apply_color_correction(apply, style)
		elif self.format in ['.dyj', '.DYJ']:
			self._osr.apply_color_correction(apply, style)
		elif self.format in ['.kfb', '.KFB']:
			self._osr.apply_color_correction(apply, style)
		elif self.format in ['.mds', '.MDS', '.mdsx', '.MDSX']:
			self._osr.apply_color_correction(apply, style)
		elif self.format in ['.tmap', '.TMAP']:
			self._osr.apply_color_correction(apply, style)
		else:
			raise NotImplementedError(f"Color correction not supported for {self.format}")


if __name__ == '__main__':
	filepath = 'path/to/your/slide'
	slide = Slide(filepath)
	print("Format : ", slide.detect_format(filepath))
	print("level_count : ", slide.level_count)
	print("level_dimensions : ", slide.level_dimensions)
	print("level_downsamples : ", slide.level_downsamples)
	print("properties : ", slide.properties)
	print("Associated Images : ")
	for key, val in slide.associated_images.items():
		print(key, " --> ", val)

	print("best level for downsample 20 : ", slide.get_best_level_for_downsample(20))
	im = slide.read_region((1000, 1000), 4, (1000, 1000))
	print(im.mode)

	im.show()
	im.close()