from setuptools import setup, find_packages

setup(
   name='mv_polar_bears',
   version='0.0.1',
   packages=find_packages(),
   include_package_data=True,
   entry_points={
       'console_scripts': [
           'mvpb-update-data = mv_polar_bears.data:update_cli',
           ]
       }
   )


