from setuptools import setup

setup(
    name="docker-menu",
    version="v0.4",
    description="Create docker container from predifined templates with dialog console interface",
    url="https://github.com/vpsua/docker-menu",
    author="vpsua",
    author_email="rnd@vps.ua",
    license="MIT",
    packages=['docker-menu'],
    install_requires=[
        "Jinja2;python2-pythondialog;PyYAML;python_version<'3'"
    ],
    python_requires='>=2.2',
)
