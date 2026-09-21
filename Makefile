.PHONY: install run test

install:
	pip install -r requirements.txt

run:
	python3 src/main.py

test:
	QT_QPA_PLATFORM=offscreen python3 -m pytest tests -v
