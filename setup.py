import io
import setuptools


setuptools.setup(
    name='distributed-worker',
    version='1.0.0',
    description=(
        'A Python wrapper around multiprocessing for easy cross-machine computation '
    ),
    author='Casper',
    author_email='casper@devdroplets.com',
    url='https://github.com/i404788/distributed-worker',
    license='BSD 2-Clause "Simplified" License',
    long_description=io.open('README.md', encoding='utf-8').read(),
    packages=['distributed_worker', 'distributed_worker.bin', 'distributed_worker.ext'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)