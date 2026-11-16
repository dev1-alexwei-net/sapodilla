FROM python:3.11-alpine
WORKDIR /app
COPY server.py /app/server.py
EXPOSE 11434
HEALTHCHECK --interval=5s --timeout=2s --retries=5 CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','11434')+'/healthz',timeout=1)" || exit 1
CMD ["python", "server.py"]
