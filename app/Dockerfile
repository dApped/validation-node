FROM python:3.7-alpine

EXPOSE 5000
EXPOSE 8765

WORKDIR app
ENTRYPOINT ["gunicorn", "-b", ":5000", "application"]

RUN \
    apk update && \
    apk add gcc linux-headers make musl-dev python3-dev py3-setuptools

COPY ./ /app/
RUN pip3 install -r requirements.txt


