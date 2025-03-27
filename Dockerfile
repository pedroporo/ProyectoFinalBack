FROM python:3.6.1
RUN pip install -r requirements.txt
CMD["python","./call_module.py"]
