FROM python:3.12-alpine
WORKDIR /app
COPY cgminer_exporter.py requirements.txt /app/
RUN pip install -r requirements.txt
CMD [ "python", "./cgminer_exporter.py" ]
