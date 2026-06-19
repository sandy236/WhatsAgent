from pydantic import BaseModel

class A(BaseModel):
    name: str = None

print('Created', A)
