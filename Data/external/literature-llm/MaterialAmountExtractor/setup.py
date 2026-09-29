from setuptools import setup, find_packages

__author__ = "Zheren Wang"
__maintainer__ = ""
__email__ = "zherenwang@berkeley.edu"

if __name__ == "__main__":
    setup(
        name="MaterialAmountExtractor",
        version="0.1.0",
        author="Zheren Wang",
        author_email="zherenwang@berkeley.edu",
        packages=find_packages(),
        zip_safe=False,
        install_requires=["chemdataextractor", "nltk"],
    )
