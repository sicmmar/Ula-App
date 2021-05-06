FROM python:alpine3.9
COPY . /api
WORKDIR /api
RUN pip install -r require.ula
EXPOSE 7050
CMD python app.py