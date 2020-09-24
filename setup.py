import setuptools

README = open('README.md').read()

setuptools.setup(
    name = 'JSON Serialize',
    version = '1.0.2',
    url = 'https://github.com/gaming32/json-serialize',
    author = 'Gaming32',
    author_email = 'gaming32i64@gmail.com',
    license = 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    description = 'Module that serializes Python objects into JSON',
    long_description = README,
    long_description_content_type = 'text/markdown',
    py_modules = [
        'json_serialize',
    ]
)
