FROM python:3.10-alpine
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 8765
COPY . .
CMD ["python","call_module.py"]
