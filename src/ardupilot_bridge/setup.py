import os

from setuptools import find_packages, setup

package_name = 'ardupilot_bridge'
setup(
    name=package_name,
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), ['launch/ardupilot_bridge.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
)
