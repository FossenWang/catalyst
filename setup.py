import re

from setuptools import setup


def read(path):
    with open(path) as fp:
        content = fp.read()
    return content


def find_version(path):
    match = re.search(r'__version__ = [\'"](?P<version>[^\'"]*)[\'"]', read(path))
    if match:
        return match.group('version')
    raise RuntimeError("Cannot find version information")


setup(
    name='catalyst',
    version=find_version('catalyst/__init__.py'),
    description="Library for converting objects to and from native Python datatypes.",
    long_description=read('README.md'),
    author="Fosssen",
    author_email="fossen@fossen.cn",
    license="MIT",
    packages=['catalyst'],
    include_package_data=False,
    zip_safe=False,
    install_requires=[],
    python_requires=">=3.5",
)
