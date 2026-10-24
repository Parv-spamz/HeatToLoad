.PHONY: setup ingest clean load features model scenarios export report test verify all

PYTHON := .venv/Scripts/python.exe
ifeq ($(OS),Windows_NT)
    PYTHON := .venv/Scripts/python.exe
else
    PYTHON := .venv/bin/python
endif

setup:
	python make.py setup

ingest:
	python make.py ingest

clean:
	python make.py clean

load:
	python make.py load

features:
	python make.py features

model:
	python make.py model

scenarios:
	python make.py scenarios

export:
	python make.py export

report:
	python make.py report

test:
	python make.py test

verify:
	python make.py verify

all:
	python make.py all
