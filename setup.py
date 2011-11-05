from setuptools import setup, find_packages

setup (
   name = 'txkqreactor',
   version = '0.2',
   description = 'Twisted kqueue reactor',
   long_description = """Twisted reactor built on select.kqueue which comes with Python since version 2.6""",
   author = 'Tavendo GmbH',
   author_email = 'txkqreactor@tavendo.de',
   url = 'https://github.com/oberstet/txkqreactor',
   platforms = ('Any'),
   install_requires = ['Twisted>=11.0'],
   packages = find_packages(),
   zip_safe = False,

   ## http://pypi.python.org/pypi?%3Aaction=list_classifiers
   ##
   classifiers = ["License :: OSI Approved :: MIT License",
                  "Development Status :: 4 - Beta",
                  "Environment :: Console",
                  "Framework :: Twisted",
                  "Intended Audience :: Developers",
                  "Operating System :: OS Independent",
                  "Programming Language :: Python",
                  "Topic :: Internet",
                  "Topic :: Software Development :: Libraries :: Python Modules"]
)
