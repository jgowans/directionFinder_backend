from setuptools import setup

setup(name='directionFinder_backend',
      version = '0.0',
      description = "Uses an antenna array and correlator to DF signals",
      url = 'https://github.com/jgowans/directionFinder_backend',
      author = "James Gowans",
      author_email = "gowans.james@gmail.com",
      license = "MIT",
      packages = ['directionFinder_backend'],
      install_requires = [
          'numpy',
          'scipy',
          'corr',
          'katcp',
          'colorlog',
      ],
      scripts = [
          'bin/run_directionFinder_backend.py',
      ],
      zip_safe = False)
