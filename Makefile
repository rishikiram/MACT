.PHONY: dev frontend backend backend-py ingest dataDict-init ingest-traceable

# Start all three processes in parallel
dev:
	@echo "Starting frontend (:3000), TypeScript backend (:3001), FastAPI backend (:8010)..."
	@trap 'kill 0' INT; \
	  (cd frontend && npm run dev) & \
	  (cd backend && npx ts-node server.ts) & \
	  (cd backend_py && uvicorn api:app --reload --port 8010) & \
	  wait

frontend:
	cd frontend && npm run dev

backend:
	cd backend && npx ts-node server.ts

# backend-py:
# 	cd backend_py && uvicorn api:app --reload --port 8010

ingest:
	python -m backend_py.ingest 

# # Bootstrap the DataDictionary table from the current studies schema
# dataDict-init:
# 	python -c "from backend_py.db import build_data_dictionary; build_data_dictionary()"