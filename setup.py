from setuptools import setup, find_packages  # noqa: H301

with open("README.md") as f:
    long_description = f.read()

setup(
    name="rasa-vier-cvg",
    version="9.9.9",
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
    install_requires=[
        'rasa-sdk',
        'aiohttp',
        'aiodns',
        'asyncio',
    ],
    packages=find_packages(),
    include_package_data=True,
    license="MIT",
)

