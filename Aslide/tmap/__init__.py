import os
FILES_DIR = os.path.join(os.path.dirname(__file__), 'lib')
FILES = [os.path.join(FILES_DIR, f) for f in os.listdir(FILES_DIR) if f.endswith('.so') and f.endswith('.h')]
