from setuptools import find_packages, setup
import os

package_name = 'jsbsim_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), ['launch/jsbsim.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'jsbsim_node = jsbsim_bridge.jsbsim_node:main',
        ],
    },
)
