from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('Testing rate limiter...')

for i in range(15):
    r = client.post('/api/v1/auth/login', json={'identifier': 'test', 'password': 'test'})
    print(f'Request {i+1}: {r.status_code}')

print(f'Storage keys: {list(app.state.rate_limit_storage.keys())}')
