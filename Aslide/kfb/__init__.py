import os
SO_FILES_DIR = os.path.join(os.path.dirname(__file__), 'lib')
SO_FILES = [os.path.join(SO_FILES_DIR, f) for f in os.listdir(SO_FILES_DIR) if f.endswith('.so')]