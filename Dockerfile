FROM python:3.7-slim

RUN pip install pipenv

COPY Pipfile* /app/
WORKDIR /app

# RUN apt add zlib
RUN pipenv install --system --deploy

COPY atlas.py .
COPY colors.py .
COPY exporter.py .

RUN useradd -ms /bin/bash minecraft
USER minecraft

ENTRYPOINT ["python", "exporter.py"]
