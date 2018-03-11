 FROM python:2.7
 ENV PYTHONUNBUFFERED 1
 RUN mkdir /code
 WORKDIR /code
 ADD requirements.txt /code/
 RUN pip install -r requirements.txt
 ADD . /code/
 RUN chmod +x /code/docker-entrypoint.sh
 ENTRYPOINT ["/code//docker-entrypoint.sh"]
 EXPOSE 8000