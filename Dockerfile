FROM python:3.12-alpine
RUN pip install tornado
COPY . .
CMD [ "python", "./cgminer_exporter.py" ]
