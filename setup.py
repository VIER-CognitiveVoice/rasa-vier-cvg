from setuptools import setup, find_packages  # noqa: H301
import os

if "VERSION" in os.environ and len(os.environ["VERSION"]) > 0:
    version = os.environ["VERSION"]
else:
    version = "0.0.1-devel"

with open("requirements.txt") as f:
    requirements = [req.strip() for req in f.readlines() if len(req) > 0]

with open("README.md") as f:
    long_description = f.read()

setup(
    name="rasa-vier-cvg",
    version=version,
    description="Rasa-integration for the VIER Cognitive Voice Gateway",
    author="VIER GmbH",
    author_email="support@vier.ai",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://cognitivevoice.io",
    project_urls={
        "Source": "https://github.com/VIER-CognitiveVoice/rasa-vier-cvg",
        "Bug Reports": "https://github.com/VIER-CognitiveVoice/rasa-vier-cvg/issues",
    },
    keywords=["VIER", "VIER Cognitive Voice Gateway SDK", "Channel"],
    python_requires=">=3.6",
    install_requires=requirements,
    packages=find_packages(),
    include_package_data=True,
    license="MIT",
)

