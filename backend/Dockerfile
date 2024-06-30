FROM python:3.11.7@sha256:63bec515ae23ef6b4563d29e547e81c15d80bf41eff5969cb43d034d333b63b8

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install uv
RUN uv venv /venv
COPY requirements.txt requirements.txt
ENV VIRTUAL_ENV=/venv
RUN uv pip install -r requirements.txt

COPY . code
WORKDIR /code

EXPOSE 8000

# runs the dev server
CMD uv venv /venv && python manage.py runserver