from pathlib import Path
from setuptools import setup

version = "7.0.0a3.dev0"

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
        "Framework :: Plone :: 6.2",
        "Framework :: Plone :: Core",
        "Framework :: Zope :: 5",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    keywords="plone layout viewlet",
    author="Plone Foundation",
    author_email="plone-developers@lists.sourceforge.net",
    url="https://pypi.org/project/plone.app.layout",
    license="GPL version 2",
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.10",
    install_requires=[
        "lxml",
        "plone.app.content",
        "plone.app.dexterity",
        "plone.app.linkintegrity",
        "plone.app.registry",
        "plone.app.relationfield",
        "plone.app.workflow",
        "plone.app.uuid",
        "plone.app.viewletmanager >=1.2",
        "plone.autoform",
        "plone.base >=4.0.0a1",
        "plone.batching",
        "plone.dexterity",
        "plone.folder",
        "plone.formwidget.namedfile",
        "plone.i18n",
        "plone.locking",
        "plone.memoize",
        "plone.portlets",
        "plone.protect",
        "plone.registry",
        "plone.supermodel",
        "plone.uuid",
        "Products.CMFEditions >=1.2.2",
        "Products.GenericSetup",
        "Products.statusmessages",
        "Products.ZCatalog",
        "z3c.form",
        "Zope",
    ],
    extras_require=dict(
        test=[
            "plone.app.contenttypes[test]",
            "plone.app.linkintegrity",
            "plone.app.relationfield",
            "plone.app.robotframework",
            "plone.app.testing",
            "plone.app.z3cform",
            "plone.app.textfield",
            "plone.browserlayer",
            "plone.dexterity",
            "plone.locking",
            "plone.namedfile",
            "plone.testing",
            "robotsuite",
            "z3c.relationfield",
            "zope.annotation",
            "zc.relation",
            "zope.intid",
        ]
    ),
)
