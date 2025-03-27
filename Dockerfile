FROM python:3.6-onbuild
RUN mkdir "/usr/src/app"
WORKDIR "/usr/src/app"
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD["python","./call_module.py"]
