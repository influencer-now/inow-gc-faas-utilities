# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

_requirements = {
    "base": ["marshmallow_dataclass==8.3.2", "marshmallow-enum==1.5.1"],
    "datastore": ["google-cloud-firestore==2.4.0"],
    "comm": ["requests", "google-cloud-pubsub==2.9.0"],
}


def _join_arrays(*args):
    out = []
    for arg in args[0]:
        out += arg
    return out


setup(
    name="inowfaasutils",
    version="0.0.17",
    description="Influencer Now Google Cloud FaaS Utilities",
    author="Iván Huerta",
    author_email="contacto@influencernow.cl",
    license="unlicense",
    packages=find_packages(),
    extras_require={
        "all": _join_arrays(_requirements.values()),
        "faasjob": _requirements["base"]
        + _requirements["datastore"]
        + _requirements["comm"],
        "comm": _requirements["base"] + _requirements["comm"],
        "datastore": _requirements["base"] + _requirements["datastore"],
    },
    zip_safe=False,
    python_requires=">=3.8",
)
