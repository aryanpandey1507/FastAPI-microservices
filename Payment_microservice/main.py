from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks

from redis_om import get_redis_connection , HashModel
from starlette.requests import Request
import requests,time

app=FastAPI()

app.add_middleware(
   CORSMiddleware,
   allow_origins=['http://localhost:3000'],
   allow_methods=['*'],
   allow_headers=['*']
)

# This should be a different database
redis = get_redis_connection(
   host = 'DUMMY_HOST_LINK',
   port=18008,
   password='DUMMY_PASSWORD',
   decode_responses=True
)

class Order(HashModel):
    product_id : str
    price:float
    fee:float 
    total:float
    quantity:int
    status:str      #pending,completed , refunded 

    class Meta:
        database = redis



@app.get('/orders/{pk}')
def get(pk:str):
    return Order.get(pk)
   

@app.post('/orders')
async def create(request:Request,background_tasks:BackgroundTasks):    # id , quantity
    body  = await request.json()

#sending get request to inventory microservice , this is the internal http request

    req=requests.get('http://localhost:8000/products/%s' % body['id'])
    product  = req.json()

    
    order = Order(
        product_id = body['id'],
        price=product['price'],
        fee= 0.2 * product['price'],
        total= 1.2*product['price'],
        quantity=body['quantity'],
        status='pending'
    )
    order.save()

    #creating the background task so that the order status will be evalutated and changed to completed in the backgorund and till then it will show pending
    background_tasks.add_task(order_completed,order)

    return order

def order_completed(order:Order):
    time.sleep(10)
    order.status='completed'
    order.save()

    #this is a producing service
    #redis stream - messaging tool for microservice interaction
    #adding a check-in stream..
    redis.xadd('order_completed',order.dict(),'*')

    # '*' defines the redis to give this entry a unique id ,timestamp and a sequence number
