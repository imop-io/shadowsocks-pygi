from setuptools import setup, find_packages

version = '0.0.1'

setup(
    name='shadowsocks-pygi',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    author='songww',
    author_email='sww4718168@gmail.com',
    url='https://github.com/songww/shadowsocks-pygi',
    license='http://opensource.org/licenses/GPL-3.0',
    description='ShadowSocks Gtk Client',
    package_data={
        'shadowsocks_pygi': ['resources/*']
    },
    install_requires=['shadowsocks', 'PyYAML', 'requests[socks]'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: X11 Applications',
        'Environment :: X11 Applications :: Gnome',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: Chinese (Simplified)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet',
        ],
    entry_points={
        'gui_scripts': [
            'shadowsocks-pygi = shadowsocks_pygi:main',
        ]
    }
)
