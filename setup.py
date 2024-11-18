import pathlib

from setuptools import setup

pkg_name = 'trio_util'
base_dir = pathlib.Path(__file__).parent
with open(base_dir / 'src' / pkg_name / '_version.py') as f:
    version_globals = {}
    exec(f.read(), version_globals)
    version = version_globals['__version__']

setup(
    name=pkg_name,
    description='Utility library for the Trio async/await framework',
    long_description='''
An assortment of utilities for the Trio async/await framework, including:

  * wait_any, wait_all, move_on_when - avoid nursery blocks for simple cases
  * AsyncBool, AsyncValue - value wrappers with the ability to wait for
    a specific value or transition
  * periodic - periodic loop which accounts for its own execution
    time
  * @trio_async_generator - decorator which adapts a generator containing
     Trio constructs for safe use
  * azip, azip_longest - async zip with parallel iteration
  * RepeatedEvent - if you really, really want to reuse an event
  * and more (... obscure stuff you probably don't need)!
''',
    long_description_content_type='text/markdown',
    version=version,
    author='GROOVE X, Inc.',
    author_email='gx-sw@groove-x.com',
    url='https://github.com/groove-x/trio-util',
    license='MIT',
    packages=[pkg_name],
    package_dir={'': 'src'},
    install_requires=[
        'async_generator',
        'trio >= 0.11.0'
    ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Framework :: Trio',
    ],
)
