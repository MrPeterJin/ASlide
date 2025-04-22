import os

from openslide import OpenSlide
from Aslide.kfb.kfb_slide import KfbSlide 
from Aslide.tmap.tmap_slide import TmapSlide
from Aslide.sdpc.sdpc_slide import SdpcSlide


class Slide(object):
	def __init__(self, filepath):
		self.filepath = filepath
		self.format = os.path.splitext(os.path.basename(filepath))[-1]

		# try reader one by one

		read_success = False

		# 1. openslide
		try:
			self._osr = OpenSlide(filepath)
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
		if hasattr(self._osr, 'get_scan_scale'):
			return self._osr.get_scan_scale
		else:
			if hasattr(self._osr, 'properties'):
				if 'openslide.mpp-x' in self._osr.properties:
					mpp = float(self._osr.properties['openslide.mpp-x'])

					return 20 if abs(mpp - 0.5) < abs(mpp - 0.25) else 40
					
		raise Exception("%s Has no attribute %s" % (self._osr.__class__.__name__, "get_scan_scale"))		

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

	def label_image(self, save_path):
		if self.format in ['.tmap', '.TMAP']:
			return self._osr.associated_images('label').save(save_path)
		elif self.format in ['.sdpc', '.SDPC']:
			return self._osr.saveLabelImg(save_path)
		else:
			return self._osr.associated_images.get('label', None).save(save_path)

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
