FROM python:2.7-alpine
RUN pip install tornado
COPY . .
CMD [ "python", "./cgminer_exporter.py" ]
