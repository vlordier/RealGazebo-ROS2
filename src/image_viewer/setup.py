from setuptools import find_packages, setup

package_name = 'image_viewer'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='kmk',
    maintainer_email='kmk6061602@naver.com',
    description='RealGazebo RTSP image viewer for drone camera streams',
    license='GPL-3.0-only',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'image_viewer = image_viewer.image_viewer:main'
        ],
    },
)
