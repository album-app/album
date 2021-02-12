import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hips",
    version="0.1.0",
    author="Kyle Harrington",
    author_email="hip@kyleharrington.com",
    description="Helmholtz Imaging Platform Solutions framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/ida-mdc/hips",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    install_requires=['pyyaml', 'xdg'],
    python_requires='>=3.8',
)
