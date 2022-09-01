from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in simple_stock/__init__.py
from simple_stock import __version__ as version

setup(
	name="simple_stock",
	version=version,
	description="Simplifies the stock module of ERPNext",
	author="Bantoo and Contributors",
	author_email="devs@thebantoo.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
