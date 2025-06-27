# Raster Maker

Web App to create and view raster data from Point-Based csv data

## How to run locally

*Warning: Local running requires some sql db. For small data testing, install and use sqlite*

1. In one shell window, run the backend:

**python/pip 1-2**
```shell
cd backend
pip install -r requirements.txt
python main.py
```

**python/pip 3**
```shell
cd backend
pip3 install -r requirements.txt
python3 main.py
```



2. In a separate shell window, run the frontend:

```shell
cd frontend
npm install
export VITE_API_ENDPOINT="http://0.0.0.0:8080"
npm run dev
```

