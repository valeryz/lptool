from setuptools import setup, find_packages
import sys

dependencies=[]
if sys.version_info < (2, 7):
    dependencies.append('argsparse')

setup(name='lptools',
      author='Valeriy Zamarayev',
      author_email='valeriy.zamarayev@gmail.com',
      package_dir = {'' : 'src'},
      py_modules=['lptools'],
      install_requires=dependencies,
      entry_points={
        'console_scripts' : ['lptasks = lptools:tasks']
        })
