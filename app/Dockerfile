FROM python:3.7-alpine as base

FROM base as builder

RUN apk update && \
    apk add gcc linux-headers make musl-dev python3-dev py3-setuptools
COPY ./requirements.txt /requirements.txt
# [1] TODO this triggers web3 error as it is implemented poorly
#RUN pip3 install --install-option="--prefix=/install" -r /requirements.txt
RUN pip3 install -r /requirements.txt


FROM base

EXPOSE 5000
EXPOSE 8765

WORKDIR app
ENTRYPOINT ["gunicorn", "-b", ":5000", "-t", "1000", "-k", "gevent", "--access-logfile '-'", "application"]

# TODO related to [1], when it will work copy from predefined place
#COPY --from=builder /install /usr/local
COPY --from=builder /usr/local /usr/local
COPY ./ /app/
