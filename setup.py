from setuptools import setup

setup(
    name='Flask_Fossen',
    version='0.1',
    description = "Fossen's restful flask extension",
    long_description=__doc__,
    author = "Fosssen",
    author_email = "fossen@fossen.cn",
    packages=['flask_fossen'],
    include_package_data=False,
    zip_safe=False,
    install_requires=[
        'Flask>=1.0',
        'Flask-SQLAlchemy>=2.3.2',
        'Flask-JWT-Extended>=3.9.1',
        'Flask-Migrate>=2.1.1',
    ]
)