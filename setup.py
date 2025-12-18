from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kliamka",
    version="0.3.0",
    author="Volodymyr Hotsyk",
    author_email="git@hotsyk.com",
    description="Small Python CLI library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hotsyk/kliamka",
    py_modules=["kliamka"],
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0.0"
    ],
)
