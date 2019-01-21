import json
from src.endpoints import whether
import src.constants


def route(event, context):

    # Get params
    path = event['path']
    params = event['queryStringParameters']

    if path == '/whether':
        directions_response = whether.whether_handler(params)
        return create_response(directions_response, 200)

    return create_response(event)


def create_response(body='', status=400):
    response = {
        'statusCode': status,
        'body': json.dumps(body),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
    }
    return response

if __name__=='__main__':
    print(route(json.loads(src.constants.test_event), ''))
