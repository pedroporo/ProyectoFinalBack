FROM python:3.6-onbuild

RUN pip install -r requirements.txt
CMD["python","./call_module.py"]
