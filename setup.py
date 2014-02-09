from setuptools import find_packages, setup

with open("README") as readme:
    setup(
        name = "pydeposits",
        version = "1.1.2",

        license = "GPL",
        description = readme.readline().strip(),
        long_description = readme.read().strip(),
        url = "https://github.com/KonishchevDmitry/pydeposits",

        install_requires = [ "pcli >= 0.2", "xlrd" ],

        author = "Dmitry Konishchev",
        author_email = "konishchev@gmail.com",

        packages = find_packages(),
        entry_points = {
            "console_scripts": [ "pydeposits = pydeposits.main:main" ],
        },
    )
