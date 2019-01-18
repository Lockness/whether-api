import json

def lambda_handler(event, context):
    response = {
        'statusCode': 200,
        'body': json.dumps(event),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

    return response
