import uvicorn
import logging.config

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    logger.info('Starting FastAPI Server')
    uvicorn.run('main:app',
                host='0.0.0.0',
                port=8000,
                workers=3,
                reload=True)
