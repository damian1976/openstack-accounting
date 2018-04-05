"""A setuptools based setup module.

"""

# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='acct',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.0',

    description='Openstack accounting',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/damian1976/openstack-accounting',

    # Author details
    author='The Python Packaging Authority',
    author_email='damian@man.poznan.pl',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4.3',
    ],

    # What does your project relate to?
    keywords='Openstack accounting',

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['Babel==2.5.1',
                      'PyYAML==3.12',
                      'argparse==1.4.0',
                      'certifi==2017.7.27.1',
                      'configparser==3.5.0',
                      'idna==2.6',
                      'iso8601==0.1.12',
                      'keystoneauth1==3.2.0',
                      'msgpack-python==0.4.8',
                      'netaddr==0.7.19',
                      'oslo.config==4.13.0',
                      'oslo.i18n==3.18.0',
                      'oslo.serialization==2.21.0',
                      'oslo.utils==3.30.0',
                      'pbr==3.1.1',
                      'pyparsing==2.2.0',
                      'python-dateutil==2.6.1',
                      'python-keystoneclient==3.13.0',
                      'python-novaclient==9.1.0',
                      'python-glanceclient==2.9.1',
                      'pytz==2017.2',
                      'requests==2.18.4',
                      'rfc3986==1.1.0',
                      'simplejson==3.11.1',
                      'six==1.11.0',
                      'urllib3==1.22',
                      'wheel==0.24.0',
                      'wrapt==1.10.11',
                    ],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'sample': ['config.ini',
                   'util/__init__.py',
                   'util/company.py',
                   'util/os_data.py',
                   'util/project.py',
                   'util/server.py',
                  ],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    #data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'acct=acct:main',
        ],
    },
)
