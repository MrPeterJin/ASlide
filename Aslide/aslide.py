import os

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

		# 4. sdpc
		if not read_success and self.format in ['.sdpc', '.SDPC']:
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

		# 9. dyj (德普特 WSI format)
		if not read_success and self.format in ['.dyj', '.DYJ']:
			try:
				self._osr = DyjSlide(filepath)
				read_success = True
			except:
				pass

		# 10. openslide (fallback for generic formats)
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

		# Fallback to get_scan_scale for compatibility
		if hasattr(self._osr, 'get_scan_scale'):
			return self._osr.get_scan_scale

		# Fallback to properties
		if hasattr(self._osr, 'properties'):
			if 'openslide.mpp-x' in self._osr.properties and 'openslide.mpp-y' in self._osr.properties:
				mpp_x = float(self._osr.properties['openslide.mpp-x'])
				mpp_y = float(self._osr.properties['openslide.mpp-y'])
				return (mpp_x + mpp_y) / 2
			elif 'openslide.mpp-x' in self._osr.properties:
				return float(self._osr.properties['openslide.mpp-x'])

		raise Exception("%s Has no attribute %s" % (self._osr.__class__.__name__, "mpp"))

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

		if hasattr(self._osr, 'associated_images'):
			assoc = self._osr.associated_images

			# Handle different interface types
			if callable(assoc):
				# TMAP-style method interface - convert to dict
				result = {}
				for tag in ['thumbnail', 'label', 'macro']:
					try:
						img = assoc(tag)
						if img is not None:
							result[tag] = img
					except:
						pass
				# Cache the result
				self._cached_associated_images = result
				return result
			else:
				# Standard dict interface (KFB, SDPC)
				# For KFB, preload all images to avoid "closed slide" errors
				if hasattr(assoc, '_keys') and hasattr(assoc, '__getitem__'):
					# This is likely a KFB _AssociatedImageMap - preload all images
					result = {}
					try:
						keys = assoc._keys()
						for key in keys:
							try:
								result[key] = assoc[key]
							except:
								pass
						# Cache the preloaded result
						self._cached_associated_images = result
						return result
					except:
						# If preloading fails, return the original object (but don't cache it)
						return assoc
				else:
					# Standard dict (SDPC) - cache it
					self._cached_associated_images = assoc
					return assoc
		else:
			# Cache empty dict
			self._cached_associated_images = {}
			return {}

	def label_image(self, save_path):
		if self.format in ['.tmap', '.TMAP']:
			return self._osr.associated_images('label')
		elif self.format in ['.sdpc', '.SDPC']:
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
		:return: PIL.Image object
		"""
		return self._osr.read_region(location, level, size)

	def read_fixed_region(self, location, level, size):
		"""
		return region image
		:param location:  (tuple) – (x, y) tuple giving the top left pixel in the level 0 reference frame
		:param level:  (int) – the level number
		:param size:  (tuple) – (width, height) tuple giving the region size
		:return: PIL.Image object
		"""
		return self._osr.read_fixed_region(location, level, size)

	def close(self):
		self._osr.close()

	def apply_color_correction(self, apply=True, style="Real"):
		"""
		Apply or disable color correction (SDPC only)

		Args:
			apply: Whether to apply color correction
			style: Color correction style ("Real" or "Gorgeous")
		"""
		if self.format in ['.sdpc', '.SDPC']:
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