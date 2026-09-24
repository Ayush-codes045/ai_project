FROM python:3.12-slim

RUN pip install pytest

WORKDIR /workspace

# Run as non-root user for security
RUN useradd -m sandboxuser
USER sandboxuser

CMD ["python", "-c", "print('sandbox ready')"]