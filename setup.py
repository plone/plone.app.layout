from pathlib import Path
from setuptools import find_packages
from setuptools import setup


version = "5.0.0"

long_description = (
    f"{Path('README.rst').read_text()}\n{Path('CHANGES.rst').read_text()}"
)

setup(
    name="plone.app.layout",
    version=version,
    description="Layout mechanisms for Plone",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    # Get more strings from
    # https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 6 - Mature",
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 6.0",
        "Framework :: Plone :: Core",
        "Framework :: Zope :: 5",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="plone layout viewlet",
    author="Plone Foundation",
    author_email="plone-developers@lists.sourceforge.net",
    url="https://pypi.org/project/plone.app.layout",
    license="GPL version 2",
    packages=find_packages(),
    namespace_packages=["plone", "plone.app"],
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.8",
    install_requires=[
        "plone.app.content",
        "plone.app.dexterity",
        "plone.app.relationfield",
        "plone.app.uuid",
        "plone.app.viewletmanager >=1.2",
        "plone.base >=1.0.4",
        "plone.dexterity",
        "plone.formwidget.namedfile",
        "plone.i18n",
        "plone.memoize",
        "plone.portlets",
        "plone.protect",
        "Products.CMFEditions >=1.2.2",
        "Products.statusmessages",
        "Products.ZCatalog",
        "setuptools",
        "Zope",
    ],
    extras_require=dict(
        test=[
            "plone.app.contenttypes[test]",
            "plone.app.relationfield",
            "plone.app.testing",
            "plone.dexterity",
            "plone.locking",
            "plone.testing",
            "z3c.relationfield",
            "zope.intid",
        ]
    ),
)
