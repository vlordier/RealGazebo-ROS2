from setuptools import find_packages, setup
setup(
    name='jsbsim_bridge',
    version='0.1.0',
    packages=find_packages(),
    data_files=[('share/ament_index/resource_index/packages', ['resource/jsbsim_bridge']),
                ('share/jsbsim_bridge', ['package.xml'])],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'jsbsim_node = jsbsim_bridge.jsbsim_node:main',
        ],
    },
)
