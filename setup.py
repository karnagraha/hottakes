from setuptools import setup

project_name = "streamer"

setup(
    name=project_name,
    version="0.1",
    packages=[project_name],
    license="BSD",
    tests_require=["pytest"],
    test_suite=f"{project_name}.tests",
)
