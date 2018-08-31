FROM python:3.7-alpine3.7

EXPOSE 5000

WORKDIR app

COPY * /app/

RUN apk update
# apk has named gunicorn as py-gunicorn
RUN apk add gcc linux-headers make musl-dev python-dev py-gunicorn

RUN pip install -r requirements.txt

CMD ["gunicorn", "-b", ":5000", "app/application"]
# only local
#CMD ["python", "application.py"]