from setuptools import find_packages, setup
from setuptools.command.test import test as Test


class PyTest(Test):
    def finalize_options(self):
        Test.finalize_options(self)
        self.test_args = ["tests"]
        self.test_suite = True

    def run_tests(self):
        import pytest
        pytest.main(self.test_args)


with open("README") as readme:
    setup(
        name="pydeposits",
        version="1.3.3",

        license="GPL",
        description=readme.readline().strip(),
        long_description=readme.read().strip(),
        url="https://github.com/KonishchevDmitry/pydeposits",

        install_requires=["pcli >= 0.2", "requests", "xlrd"],

        author="Dmitry Konishchev",
        author_email="konishchev@gmail.com",

        packages=find_packages(),
        entry_points={
            "console_scripts": ["pydeposits = pydeposits.main:main"],
        },

        cmdclass={"test": PyTest},
        tests_require=["pytest"],
    )
