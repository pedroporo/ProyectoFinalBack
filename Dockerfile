FROM python:3.11
WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8765
COPY . .
