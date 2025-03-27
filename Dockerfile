FROM python:3.6
WORKDIR /testcall
COPY requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8765
COPY . .
CMD["python","call_module.py"]
