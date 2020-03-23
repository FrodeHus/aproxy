package:
	rm -Rf dist/
	python3 setup.py sdist bdist_wheel --bdist-dir ~/temp/bdistwheel

upload_test:
	python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

upload:
	python3 -m twine upload dist/*
