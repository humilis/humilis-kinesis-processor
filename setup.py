"""Setuptools entrypoint."""
import codecs
import os

from setuptools import setup, find_packages

from humilis_kinesis_processor import __version__

dirname = os.path.dirname(__file__)

long_description = (
    codecs.open(os.path.join(dirname, "README.rst"), encoding="utf-8").read() + "\n" +   # noqa
    codecs.open(os.path.join(dirname, "AUTHORS.rst"), encoding="utf-8").read() + "\n" +  # noqa
    codecs.open(os.path.join(dirname, "CHANGES.rst"), encoding="utf-8").read()
)

setup(
    name="humilis-kinesis-processor",
    include_package_data=True,
    package_data={"": ["*.j2", "*.yaml"]},
    packages=find_packages(include=['humilis_kinesis_processor',
                                    'humilis_kinesis_processor.*']),
    version=__version__,
    author="Anatoly Bubenkov, FindHotel and others",
    author_email="developers@innovativetravel.eu",
    url="http://github.com/humilis/humilis-kinesis-processor",
    license="MIT",
    description="Humilis kinesis stream processor plugin",
    long_description=long_description,
    install_requires=[
        "humilis>=0.7.5"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2"
    ],
    zip_safe=False,
    entry_points={
        "humilis.layers": [
            "kinesis-processor="
            "humilis_kinesis_processor.plugin:get_layer_path"]}
)
