import setuptools

__version__ = None
with open("aproxy/version.py") as f:
    exec(f.read())

setuptools.setup(
    name="aproxy",
    version=__version__,
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": ["aproxy=aproxy.__main__:main"]},
    author="Frode Hus",
    author_email="frode.hus@outlook.com",
    description="Simple tool that lets you run multiple proxies simultaneously",
    url="https://github.com/frodehus/aproxy",
    python_requires=">=3.6",
    install_requires=["hexdump", "colorama", "knack",],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
