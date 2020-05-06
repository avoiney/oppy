from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='OpPy',
    version='0.1.0',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/avoiney/oppy',
    author='Alexandre Voiney',
    author_email='bonjour@alexandre.voiney.fr',
    classifier=[
        'Development Status :: 3 - Alpha',
        'License :: MIT Licence'
    ],
    keywork='One Password, password manager',
    packages=find_packages(),
    install_requires=['cryptography', 'dbus-python', 'ply',
                      'keyring', 'Pygments', 'SecretStorage'],
    entry_points={
        'console_scripts': [
            'oppy=oppy:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/avoiney/oppy/issues',
        'Source': 'https://github.com/avoiney/oppy'
    }
)
