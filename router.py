import json
from src.endpoints import whether
import src.constants


def route(event, context):
    print(event)
    # Get params
    params = event['queryStringParameters']

    directions_response = whether.whether_handler(params)
    return create_response(directions_response, 200)


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
